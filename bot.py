import logging
import asyncio
import nest_asyncio
import aiosqlite
from geopy.distance import geodesic
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    InputMediaPhoto,
    Bot,
    BotCommandScopeChat,
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

# Apply nest_asyncio for Jupyter/Notebook environments
nest_asyncio.apply()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak")
DATABASE = os.getenv("DATABASE", "users.db")
ADMIN_ID = 1796978458
BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# List of countries and cities
COUNTRIES = {
    "السودان": [
        "الخرطوم", "أم درمان", "بحري", "بورتسودان", "كسلا", "القضارف", "ود مدني", 
        "الأبيض", "نيالا", "الفاشر", "دنقلا", "عطبرة", "كوستي", "سنار", "الضعين",
        "الدمازين", "شندي", "كريمة", "طوكر", "حلفا الجديدة", "وادي حلفا", "أم روابة",
        "أبو جبيهة", "بابنوسة", "الجنينة", "جزيرة توتي", "الحصاحيصا", "رفاعة", "سنجة",
        "الرنك", "حلفا", "الحديبة", "تندلتي", "الدلنج", "كادوقلي", "بنتيو", "الرهد",
        "نوري", "أرقين", "خشم القربة", "النهود", "مروي", "سواكن", "حلايب", "أبورماد",
        "عبري", "كتم", "الضعين", "المجلد", "كرنوي", "زالنجي"
    ],
    "مصر": ["القاهرة", "الإسكندرية", "الجيزة", "شرم الشيخ"],
    "السعودية": ["الرياض", "جدة", "مكة", "المدينة المنورة"],
    "ليبيا": ["طرابلس", "بنغازي", "مصراتة", "سبها"],
    "الإمارات": ["دبي", "أبوظبي", "الشارقة", "عجمان"]
}

# Conversation states
USERNAME, NAME, AGE, BIO, TYPE, COUNTRY, CITY, LOCATION, PHOTO = range(9)
FEEDBACK, REPORT = range(2)

async def show_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display comprehensive terms and conditions"""
    terms_text = """
    📜 *شروط وأحكام استخدام تطبيق تحديقة*:

    1. 🧔 **الشروط الأساسية**:
       - يجب أن يكون عمرك 18+ سنة.
       - يُحظر انتحال شخصية الآخرين أو استخدام حسابات وهمية.

    2. 🚫 **الممنوعات الصارمة**:
       - التحرش أو المضايقات بأي شكل.
       - المحتوى السياسي أو الطائفي.
       - الاحتيال أو طلب الأموال.

    3. 🔐 **حماية البيانات**:
       - نحتفظ ببياناتك طوال مدة استخدامك للتطبيق.
       - يمكنك طلب حذف بياناتك عبر مراسلة الإدارة.
       - لا نشارك بياناتك مع أطراف خارجية.

    4. ⚠️ **العقوبات**:
       - أي مخالفة تؤدي إلى إيقاف حسابك فوراً.
       - يمكنك الإبلاغ عن المخالفين عبر خاصية الإبلاغ.

    *بموافقتك، أنت توافق على هذه الشروط بشكل كامل.*
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ أوافق على الشروط", callback_data="agree_to_privacy")],
        [InlineKeyboardButton("❌ رفض الشروط", callback_data="decline_terms")]
    ]
    
    await update.message.reply_text(
        terms_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return USERNAME

async def decline_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user declines terms"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ لم توافق على الشروط. لا يمكنك استخدام التطبيق.")
    return ConversationHandler.END

async def init_db():
    """Initialize database with proper error handling and migrations"""
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            
            # Create tables if they don't exist
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
            
            # ... (rest of your existing database initialization code)
            
            await db.commit()
            logger.info("Database initialized successfully.")
            await backup_database()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    # Check if user already exists and is not banned/frozen
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT banned, frozen FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            user_status = await cursor.fetchone()
            
            if user_status:
                if user_status[0]:  # banned
                    await update.message.reply_text("❌ حسابك محظور. لا يمكنك استخدام التطبيق.")
                    return ConversationHandler.END
                elif user_status[1]:  # frozen
                    await update.message.reply_text("❄️ حسابك مجمد مؤقتًا. الرجاء التواصل مع الإدارة.")
                    return ConversationHandler.END
                else:
                    await update.message.reply_text(
                        "مرحبًا بك مرة أخرى! يمكنك استخدام /search للبحث عن أشخاص قريبين."
                    )
                    return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error checking user registration: {e}")
    
    # Show terms and conditions
    await show_terms(update, context)
    return USERNAME

# ... (keep all your existing functions like agree_to_privacy, set_username, etc.)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Try to notify the user about the error
    try:
        if update and hasattr(update, 'effective_chat'):
            text = (
                "⚠️ حدث خطأ غير متوقع أثناء معالجة طلبك.\n"
                "تم إبلاغ الإدارة وسيتم حل المشكلة قريبًا."
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text
            )
    except Exception as e:
        logger.error("Error while trying to notify user about error:", exc_info=e)
    
    # Notify admin about the error
    try:
        error_text = (
            f"⚠️ حدث خطأ في التطبيق:\n\n"
            f"Update: {update}\n"
            f"Context: {context}\n"
            f"Error: {context.error}"
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=error_text
        )
    except Exception as e:
        logger.error("Error while trying to notify admin about error:", exc_info=e)

async def main():
    # Initialize database
    await init_db()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Registration handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [
                CallbackQueryHandler(agree_to_privacy, pattern="^agree_to_privacy$"),
                CallbackQueryHandler(decline_terms, pattern="^decline_terms$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_username)
            ],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_age)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_bio)],
            TYPE: [CallbackQueryHandler(set_type)],
            COUNTRY: [CallbackQueryHandler(set_country)],
            CITY: [CallbackQueryHandler(set_city)],
            LOCATION: [MessageHandler(filters.LOCATION, set_location)],
            PHOTO: [MessageHandler(filters.PHOTO, set_photo)],
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )

    # ... (keep all your existing handler setups)

    # Add all handlers
    application.add_handler(conv_handler)
    application.add_handler(feedback_handler)
    application.add_handler(report_handler)
    application.add_handler(CommandHandler('search', show_nearby_profiles))
    application.add_handler(CommandHandler('admin', admin_panel))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())