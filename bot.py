import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler

# Replace with your actual bot token
TOKEN = "7332555745:AAHdJ6hUQbVmwLL_r3NE2erKHFQFn90vRoU"

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    # Arabic message welcoming users
    welcome_message = "مرحباً! كيف يمكنني مساعدتك؟"
    await update.message.reply_text(welcome_message)

    # Create a custom keyboard (menu buttons)
    keyboard = [
        [KeyboardButton("/ابدأ"), KeyboardButton("/مساعدة")],
        [KeyboardButton("/معلومات"), KeyboardButton("/اتصل")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # Send a message with the custom keyboard
    await update.message.reply_text("اختر أحد الخيارات:", reply_markup=reply_markup)

# Define the /help command handler
async def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    help_message = "اكتب /ابدأ للبدء. أو اختر أحد الخيارات من القائمة."
    await update.message.reply_text(help_message)

# Define the /info command handler
async def info_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /info is issued."""
    info_message = "هذه معلومات حول البوت."
    await update.message.reply_text(info_message)

# Define the /contact command handler
async def contact_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /contact is issued."""
    contact_message = "تواصل معنا عبر البريد الإلكتروني: support@example.com"
    await update.message.reply_text(contact_message)

# Function to handle messages
async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handle user messages that are not commands."""
    user_message = update.message.text
    response_message = f"لقد قلت: {user_message}"
    await update.message.reply_text(response_message)

# Main function to set up and run the bot
async def main() -> None:
    """Run the Telegram bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("ابدأ", start))
    application.add_handler(CommandHandler("مساعدة", help_command))
    application.add_handler(CommandHandler("معلومات", info_command))
    application.add_handler(CommandHandler("اتصل", contact_command))

    # Add a message handler to reply to non-command messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot (polling for new updates)
    await application.run_polling()

# Entry point of the script
if __name__ == "__main__":
    try:
        # Running the bot using asyncio.run
        asyncio.run(main())
    except RuntimeError as e:
        # Handle already running event loop (common in environments like Jupyter or cloud platforms)
        if str(e) == "This event loop is already running":
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
