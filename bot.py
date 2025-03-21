import logging
import asyncio
import nest_asyncio
import aiosqlite  # Asynchronous SQLite library
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Apply nest_asyncio for event loops
nest_asyncio.apply()

# Logging for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = "YOUR_BOT_TOKEN"

# Database connection
DATABASE = "users.db"

# Admin IDs
ADMINS = [1796978458]

# Initialize database
async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                age INTEGER,
                bio TEXT,
                type TEXT,
                location TEXT,
                photo TEXT,
                tribes TEXT
            )"""
        )
        await db.commit()

# Display profile command
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        profile_data = await cursor.fetchone()

    if profile_data:
        profile_text = (f"📋 **ملفك الشخصي**\n"
                        f"👤 الاسم: {profile_data[2]}\n"
                        f"📅 العمر: {profile_data[3]}\n"
                        f"💬 نبذة: {profile_data[4]}\n"
                        f"📍 الموقع: {profile_data[6]}\n"
                        f"🌐 النوع: {profile_data[5]}\n")
        await update.message.reply_text(profile_text)
    else:
        await update.message.reply_text("❌ لم يتم العثور على ملفك الشخصي.")

# Delete profile
async def delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Delete profile button clicked")
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = query.from_user.id
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("DELETE FROM users WHERE id=?", (user_id,))
            await db.commit()
        
        await query.message.reply_text("✅ تم حذف ملفك الشخصي بنجاح.")
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        await query.message.reply_text("❌ فشل في حذف الملف الشخصي. يرجى المحاولة مرة أخرى.")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/start command received")
    try:
        user = update.message.from_user
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT * FROM users WHERE id=?", (user.id,))
            result = await cursor.fetchone()

        if not result:
            await update.message.reply_text("🔹 **يجب التسجيل أولًا لاستخدام البوت.**")
            return

        keyboard = [
            [InlineKeyboardButton("🔍 حدّق", callback_data="search"),
             InlineKeyboardButton("👥 عرض المستخدمين", callback_data="show_users")],
            [InlineKeyboardButton("📝 تعديل ملفي", callback_data="edit_profile"),
             InlineKeyboardButton("📍 تحديث موقعي", callback_data="update_location")],
            [InlineKeyboardButton("🗑️ حذف الملف الشخصي", callback_data="delete_profile"),
             InlineKeyboardButton("⚙ الإعدادات", callback_data="settings")],
            [InlineKeyboardButton("🔙 الرجوع", callback_data="go_back")]
        ]
        
        if user.id in ADMINS:
            keyboard.append([InlineKeyboardButton("🔧 لوحة الإدارة", callback_data="admin_panel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🌟 **مرحبًا بك في تحديقة!** اختر من القائمة:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# Go back
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Go back button clicked")
    query = update.callback_query
    await query.answer()
    await start(update, context)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text("❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")

# Main function
async def main():
    logger.info("Starting bot...")
    try:
        await init_db()
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        
        app.add_error_handler(error_handler)
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("profile", profile))
        app.add_handler(CallbackQueryHandler(delete_profile, pattern="^delete_profile$"))
        app.add_handler(CallbackQueryHandler(go_back, pattern="^go_back$"))
        
        await app.bot.delete_webhook()
        await app.run_polling()
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())
