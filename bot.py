import logging
import asyncio
import nest_asyncio
import aiosqlite
from geopy.distance import geodesic
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    Bot,
    ChatMember
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
import telegram.error
import os
import pandas as pd
from datetime import datetime
from io import BytesIO
import re
import sys

# Apply nest_asyncio for Jupyter/Notebook environments
nest_asyncio.apply()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
DATABASE = os.getenv("DATABASE", "users.db")
ADMIN_ID = 1796978458  # Replace with your admin ID
BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# List of countries and cities
COUNTRIES = {
    "السودان": ["الخرطوم", "أم درمان", "بحري", "بورتسودان"],
    "مصر": ["القاهرة", "الإسكندرية"],
    "السعودية": ["الرياض", "جدة"]
}

# Conversation states
(
    USERNAME, NAME, AGE, BIO, TYPE, 
    COUNTRY, CITY, LOCATION, PHOTO,
    FEEDBACK, REPORT,
    BROADCAST_MESSAGE,
    BAN_USER, FREEZE_USER, PROMOTE_USER
) = range(14)

# Admin states
ADMIN_PANEL, ADMIN_USERS = range(2)

async def init_db():
    """Initialize database with all tables"""
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    name TEXT,
                    age INTEGER,
                    bio TEXT,
                    type TEXT,
                    location TEXT,
                    photo TEXT,
                    country TEXT,
                    city TEXT,
                    telegram_id INTEGER UNIQUE,
                    banned INTEGER DEFAULT 0,
                    frozen INTEGER DEFAULT 0,
                    admin INTEGER DEFAULT 0,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            
            # Other tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    reported_user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    target_id INTEGER,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            
            await db.commit()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    if user_id == ADMIN_ID:
        return True
        
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT admin FROM users WHERE telegram_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            return result and result[0] == 1
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT banned, frozen FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            user_status = await cursor.fetchone()
            
            if user_status:
                if user_status[0]:  # banned
                    await update.message.reply_text("❌ حسابك محظور.")
                    return ConversationHandler.END
                elif user_status[1]:  # frozen
                    await update.message.reply_text("❄️ حسابك مجمد مؤقتًا.")
                    return ConversationHandler.END
                else:
                    await update.message.reply_text("مرحبًا بك مجددًا! استخدم /search للبحث.")
                    return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error checking user: {e}")
    
    # Show terms
    await show_terms(update, context)
    return USERNAME

async def show_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show terms and conditions"""
    terms = """
    📜 شروط وأحكام الاستخدام:
    1. يجب أن تكون +18
    2. لا محتوى مسيء
    3. احترام الخصوصية
    """
    keyboard = [
        [InlineKeyboardButton("✅ أوافق", callback_data="agree_terms")],
        [InlineKeyboardButton("❌ لا أوافق", callback_data="decline_terms")]
    ]
    await update.message.reply_text(
        terms, 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return USERNAME

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Complete user registration"""
    user = update.effective_user
    user_data = context.user_data
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                """INSERT INTO users (
                    username, name, age, bio, type,
                    location, photo, country, city, telegram_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_data.get('username'),
                    user_data.get('name'),
                    user_data.get('age'),
                    user_data.get('bio'),
                    user_data.get('type'),
                    user_data.get('location'),
                    user_data.get('photo'),
                    user_data.get('country'),
                    user_data.get('city'),
                    user.id
                )
            )
            await db.commit()
        
        await update.message.reply_text("🎉 تم التسجيل بنجاح! استخدم /search للبحث.")
        
        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 مستخدم جديد:\n{user_data.get('name')}\n@{user_data.get('username')}"
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التسجيل.")
    
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel main menu"""
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👤 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📢 بث رسالة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📤 تصدير البيانات", callback_data="admin_export")]
    ]
    
    await update.message.reply_text(
        "🛠 لوحة التحكم:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_admin_stats(query):
    """Show admin statistics"""
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Get counts
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
            banned_users = (await cursor.fetchone())[0]
            
            stats = (
                f"📊 الإحصائيات:\n\n"
                f"👥 إجمالي المستخدمين: {total_users}\n"
                f"⛔ محظورين: {banned_users}\n"
            )
            
            await query.edit_message_text(
                stats,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
                ])
            )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await query.edit_message_text("❌ حدث خطأ في جلب الإحصائيات.")

async def handle_admin_users(query):
    """User management menu"""
    keyboard = [
        [InlineKeyboardButton("⛔ حظر مستخدم", callback_data="admin_ban")],
        [InlineKeyboardButton("❄️ تجميد مستخدم", callback_data="admin_freeze")],
        [InlineKeyboardButton("👑 رفع مسؤول", callback_data="admin_promote")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        "👤 إدارة المستخدمين:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_broadcast(query):
    """Start broadcast process"""
    await query.edit_message_text(
        "📢 أرسل الرسالة للبث:\n"
        "أو /cancel للإلغاء",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ])
    )
    return BROADCAST_MESSAGE

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to all users"""
    user = update.effective_user
    if not await is_admin(user.id):
        return
    
    message = update.message.text
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT telegram_id FROM users WHERE banned = 0")
            users = await cursor.fetchall()
        
        success = 0
        for user_id, in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 إشعار من الإدارة:\n\n{message}"
                )
                success += 1
            except Exception as e:
                logger.error(f"Broadcast failed for {user_id}: {e}")
        
        await update.message.reply_text(f"✅ تم الإرسال لـ {success} مستخدم")
        
        # Log the broadcast
        await log_admin_action(
            user.id,
            "broadcast",
            details=f"Sent to {success} users"
        )
    
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text("❌ حدث خطأ في البث")
    
    return ConversationHandler.END

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to admin panel"""
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)
    return ConversationHandler.END

async def log_admin_action(admin_id: int, action: str, target_id: int = None, details: str = None):
    """Log admin actions"""
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (?, ?, ?, ?)",
                (admin_id, action, target_id, details)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Error logging admin action: {e}")

async def main():
    """Main application setup"""
    await init_db()
    
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .build()

    # Registration handler
    registration = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT, set_username)],
            NAME: [MessageHandler(filters.TEXT, set_name)],
            AGE: [MessageHandler(filters.TEXT, set_age)],
            BIO: [MessageHandler(filters.TEXT, set_bio)],
            TYPE: [CallbackQueryHandler(set_type)],
            COUNTRY: [CallbackQueryHandler(set_country)],
            CITY: [CallbackQueryHandler(set_city)],
            LOCATION: [MessageHandler(filters.LOCATION, set_location)],
            PHOTO: [MessageHandler(filters.PHOTO, set_photo)]
        },
        fallbacks=[CommandHandler('cancel', cancel_registration)],
        per_message=True
    )

    # Admin broadcast handler
    broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern="^admin_broadcast$")],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)]
        },
        fallbacks=[CommandHandler('cancel', admin_back)]
    )

    # Add handlers
    application.add_handler(registration)
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CallbackQueryHandler(handle_admin_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(handle_admin_users, pattern="^admin_users$"))
    application.add_handler(broadcast_handler)
    application.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    
    # Error handler
    application.add_error_handler(error_handler)

    # Start bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot is running...")
    
    # Keep running
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
