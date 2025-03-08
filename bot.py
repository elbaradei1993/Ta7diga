import logging
import asyncio
import nest_asyncio
import aiosqlite
import math
from datetime import datetime, timedelta
from telegram import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Location
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Configure environment
nest_asyncio.apply()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"
DATABASE = "users.db"
ADMIN_ID = 123456789
PHOTO_PROMPT = "📸 يرجى إرسال صورة شخصية (اختياري):\n(يمكنك تخطي هذا الخطوة بالضغط على الزر أدناه)"
SKIP_PHOTO_BUTTON = [[InlineKeyboardButton("تخطي الصورة", callback_data="skip_photo")]]
MAX_PHOTO_SIZE = 5_000_000  # 5MB

# Helper functions
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Database operations
async def init_db():
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                age INTEGER CHECK(age BETWEEN 13 AND 100),
                bio TEXT,
                type TEXT,
                lat REAL CHECK(lat BETWEEN -90 AND 90),
                lon REAL CHECK(lon BETWEEN -180 AND 180),
                photo TEXT,
                last_active DATETIME
            )""")
            await db.execute("""CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                reported_user_id INTEGER,
                resolved BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            await db.execute("""CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            await db.commit()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def update_user_activity(user_id: int):
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Activity update failed for user {user_id}: {e}")

async def is_user_online(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT last_active FROM users WHERE id = ?", (user_id,))
            last_active = await cursor.fetchone()
            
        if not last_active or not last_active[0]:
            return False
            
        last_active_time = datetime.strptime(last_active[0], "%Y-%m-%d %H:%M:%S")
        return datetime.now() - last_active_time < timedelta(minutes=5)
    except Exception as e:
        logger.error(f"Online check failed for user {user_id}: {e}")
        return False

# **************************************
# COMMAND HANDLERS (DEFINED FIRST)
# **************************************
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    try:
        await update_user_activity(update.message.from_user.id)
        user = update.message.from_user
        
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT 1 FROM users WHERE id=?", (user.id,))
            exists = await cursor.fetchone()

        keyboard = [
            [InlineKeyboardButton("🛟 المساعدة", callback_data="help_command")],
            [InlineKeyboardButton("🗑️ حذف الحساب", callback_data="delete_account")],
            [InlineKeyboardButton("📝 إنشاء/تحديث الملف الشخصي", callback_data="edit_profile")],
            [InlineKeyboardButton("🚨 الإبلاغ عن مستخدم", callback_data="report_user")],
            [InlineKeyboardButton("📩 إرسال ملاحظات", callback_data="feedback")],
            [InlineKeyboardButton("📍 مشاركة الموقع", callback_data="share_location")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✨ مرحبا! اختر أحد الخيارات التالية:", reply_markup=reply_markup)
        
        if not exists:
            await register_user(update, context)
            
    except Exception as e:
        logger.error(f"Start command error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
        help_text = (
            "🛟 *كيفية استخدام البوت:*\n\n"
            "1. ابدأ بتسجيل بياناتك باستخدام الأمر /start.\n"
            "2. شارك موقعك لرؤية المستخدمين القريبين.\n"
            "3. تصفح ملفات المستخدمين القريبين وابدأ المحادثات.\n"
            "4. استخدم /update لتحديث ملفك الشخصي.\n"
            "5. استخدم /delete لحذف حسابك.\n"
            "6. استخدم /report للإبلاغ عن مستخدم.\n"
            "7. استخدم /feedback لإرسال ملاحظاتك.\n\n"
            "📌 يمكنك تحديث قائمة المستخدمين القريبين باستخدام زر '🔄 تحديث'."
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Help command error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("DELETE FROM users WHERE id=?", (update.message.from_user.id,))
            await db.commit()
        await update.message.reply_text("✅ تم حذف حسابك بنجاح!")
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        await update.message.reply_text("❌ فشل في حذف الحساب")

# ... (Keep all other handler functions here, before main())

# **************************************
# MAIN FUNCTION (DEFINED LAST)
# **************************************
async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("delete", delete_account))
    # Add other command handlers here
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_button))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())