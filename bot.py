import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Enable logging to get detailed info about errors and events
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a start command handler to welcome users
async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Hello, I am your bot!')

# Define a help command handler
async def help(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Use /start to initiate the conversation.")

# Function to log errors
async def error(update: Update, context: CallbackContext) -> None:
    """Log the errors caused by updates."""
    logger.warning(f'Update "{update}" caused error "{context.error}"')

# Main function to set up the bot and start polling
async def main() -> None:
    """Start the bot and handle updates."""
    # Replace with your actual bot token
    TOKEN = '7332555745:AAGvky70vii-MI6KAQDOZWvLFKdNkH82t8k'

    # Create an Application object and pass it your bot's token
    application = Application.builder().token(TOKEN).build()

    # Delete any existing webhook to prevent conflicts
    await application.bot.delete_webhook()

    # Register handlers for /start, /help, and error logging
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))

    # Register the error handler
    application.add_error_handler(error)

    # Start polling for updates from Telegram
    await application.run_polling()

# Ensure this is the main script being run
if __name__ == '__main__':
    try:
        # Directly call the main function without asyncio.run or loop management
        main()  # Should work when the environment handles the event loop
    except Exception as e:
        logger.error(f"Error starting the bot: {e}")
