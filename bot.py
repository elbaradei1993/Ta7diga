import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Replace with your actual bot token
TOKEN = "7332555745:AAHdJ6hUQbVmwLL_r3NE2erKHFQFn90vRoU"

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Command Handlers
async def start(update: Update, context: CallbackContext):
    """Handle /start command."""
    welcome_message = "مرحباً! كيف يمكنني مساعدتك؟"
    keyboard = [[KeyboardButton("ابدأ")], [KeyboardButton("مساعدة"), KeyboardButton("اتصل")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: CallbackContext):
    """Handle /help command."""
    await update.message.reply_text("اكتب /start للبدء. أو اختر أحد الخيارات من القائمة.")

# Message Handlers
async def handle_message(update: Update, context: CallbackContext):
    """Handle plain text messages."""
    user_message = update.message.text
    if user_message == "ابدأ":
        await start(update, context)
    elif user_message == "مساعدة":
        await help_command(update, context)
    else:
        await update.message.reply_text(f"لقد قلت: {user_message}")

async def main():
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    await application.initialize()
    logger.info("Bot initialized")
    await application.start()
    logger.info("Bot started")
    await application.updater.start_polling()
    await application.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "This event loop is already running" in str(e):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
