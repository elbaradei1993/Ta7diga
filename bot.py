import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Enable logging for better debugging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message when /start is called."""
    await update.message.reply_text("Hello, I am تحديقة Bot! How can I assist you?")

# Define the /help command handler
async def help(update: Update, context: CallbackContext) -> None:
    """Send instructions when /help is called."""
    await update.message.reply_text(
        "Use /start to get started.\n"
        "If you have any questions, feel free to ask!"
    )

# Error handler
async def error(update: Update, context: CallbackContext) -> None:
    """Log errors and provide a message."""
    logger.warning(f'Update "{update}" caused error "{context.error}"')
    await update.message.reply_text("Oops! Something went wrong. Please try again later.")

# Main function to set up the bot and start polling
async def main() -> None:
    """Start the bot and set up the polling loop."""
    TOKEN = '7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak'  # Your new bot token

    # Initialize the application with the bot token
    application = Application.builder().token(TOKEN).build()

    # Delete any existing webhooks before starting
    await application.bot.delete_webhook()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))

    # Register error handler
    application.add_error_handler(error)

    # Start polling for updates
    await application.run_polling()

# Entry point for running the bot
if __name__ == '__main__':
    # Using the event loop already running in Railway
    asyncio.create_task(main())
