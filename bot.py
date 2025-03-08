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
ADMIN_ID = 1796978458
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
            # Tables creation code remains same
            await db.commit()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

# ... (keep previous database functions like update_user_activity, is_user_online)

# Command handlers
async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delete command"""
    try:
        await update_user_activity(update.message.from_user.id)
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("DELETE FROM users WHERE id=?", (update.message.from_user.id,))
            await db.commit()
        await update.message.reply_text("✅ تم حذف حسابك بنجاح!")
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        await update.message.reply_text("❌ فشل في حذف الحساب")

async def delete_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delete account button press"""
    try:
        query = update.callback_query
        await query.answer()
        await update_user_activity(query.from_user.id)
        
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("DELETE FROM users WHERE id=?", (query.from_user.id,))
            await db.commit()
            
        await query.edit_message_text("✅ تم حذف حسابك بنجاح!")
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        await query.edit_message_text("❌ فشل في حذف الحساب")

# ... (keep previous command handlers like start, help_command, register_user)

# Button handlers
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        await update_user_activity(query.from_user.id)

        if query.data == "delete_account":
            await delete_account_handler(update, context)
        elif query.data == "help_command":
            await help_command(query.message, context)
        elif query.data == "edit_profile":
            await edit_profile_handler(query, context)
        # ... (other button handlers)

    except Exception as e:
        logger.error(f"Button handling error: {e}")
        await query.edit_message_text("❌ حدث خطأ غير متوقع")

# Main application
async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("delete", delete_account))  # Corrected reference
    app.add_handler(CommandHandler("update", edit_profile))
    app.add_handler(CommandHandler("report", report_user))
    app.add_handler(CommandHandler("feedback", feedback))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_button))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    
    app.add_error_handler(error_handler)
    
    await app.run_polling()

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}", exc_info=True)
    if update and update.callback_query:
        await update.callback_query.answer("❌ حدث خطأ غير متوقع")
    elif update and update.message:
        await update.message.reply_text("❌ حدث خطأ غير متوقع")

if __name__ == "__main__":
    asyncio.run(main())