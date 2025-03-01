import random
import logging
import asyncio
import nest_asyncio
import sqlite3
import math
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    InputMediaPhoto,
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

# Apply nest_asyncio for event loops
nest_asyncio.apply()

# Logging for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Database connection
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Create user profiles table
cursor.execute(
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
conn.commit()

ADMINS = [1796978458]  # Admin IDs

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command & enforce registration."""
    try:
        user = update.message.from_user
        cursor.execute("SELECT * FROM users WHERE id=?", (user.id,))
        result = cursor.fetchone()

        if not result:
            await update.message.reply_text("🔹 **يجب التسجيل أولًا لاستخدام البوت.**")
            await register(update, context)
            return

        keyboard = [
            [InlineKeyboardButton("🔍 حدّق", callback_data="search"),
             InlineKeyboardButton("👥 عرض المستخدمين", callback_data="show_users")],
            [InlineKeyboardButton("📝 تعديل ملفي", callback_data="edit_profile"),
             InlineKeyboardButton("📍 تحديث موقعي", callback_data="update_location")],
            [InlineKeyboardButton("🗑️ حذف الملف الشخصي", callback_data="delete_profile"),
             InlineKeyboardButton("⚙ الإعدادات", callback_data="settings")]
        ]
        
        if user.id in ADMINS:
            keyboard.append([InlineKeyboardButton("🔧 لوحة الإدارة", callback_data="admin_panel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🌟 **مرحبًا بك في تحديقة!** اختر من القائمة:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

async def delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete user profile."""
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = query.from_user.id
        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        
        await query.message.reply_text("✅ تم حذف ملفك الشخصي بنجاح.")
        await register(update, context)
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        await query.message.reply_text("❌ فشل في حذف الملف الشخصي. يرجى المحاولة مرة أخرى.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors."""
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text("❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")

# ... [Keep all other functions the same as previous version, just add this new handler]

async def main():
    """Start bot with updated handlers."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(search, pattern="^search$"))
    app.add_handler(CallbackQueryHandler(show_users, pattern="^show_users$"))
    app.add_handler(CallbackQueryHandler(view_profile, pattern="^profile_"))
    app.add_handler(CallbackQueryHandler(handle_tap, pattern="^tap_"))
    app.add_handler(CallbackQueryHandler(select_type, pattern="^type_"))
    app.add_handler(CallbackQueryHandler(save_type, pattern="^save_type$"))
    app.add_handler(CallbackQueryHandler(skip_photo, pattern="^skip_photo$"))
    app.add_handler(CallbackQueryHandler(delete_profile, pattern="^delete_profile$"))
    
    # Stop any existing webhook
    await app.bot.delete_webhook()
    
    # Start polling
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
