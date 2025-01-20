import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Enable logging to get detailed info about errors and events
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a start command handler to welcome users
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hello, I am your bot!')

# Define a help command handler
def help(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text("Use /start to initiate the conversation.")

# Function to log errors
def error(update: Update, context: CallbackContext) -> None:
    """Log the errors caused by updates."""
    logger.warning(f'Update "{update}" caused error "{context.error}"')

# Main function to set up the bot and start polling
def main() -> None:
    """Start the bot and handle updates."""
    # Replace with your actual bot token
    TOKEN = '7332555745:AAGvky70vii-MI6KAQDOZWvLFKdNkH82t8k'

    # Create an Updater object and pass it your bot's token
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register handlers for /start, /help, and error logging
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))

    # Register the error handler
    dispatcher.add_error_handler(error)

    # Start polling for updates from Telegram
    updater.start_polling()

    # Run the bot until you press Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()
