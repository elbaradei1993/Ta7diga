import logging
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Bot token (updated as per your provided token)
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Command to start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text("Welcome to تحديقة! Use /connect to start a random video chat.")

# Command to connect users via random Jitsi video chat
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send a random Jitsi meet link."""
    jitsi_base_url = "https://meet.jit.si/"
    random_meeting_id = f"Tahdiqa_{update.effective_user.id}"
    jitsi_link = jitsi_base_url + random_meeting_id
    await update.message.reply_text(f"Your random video chat link: {jitsi_link}")

# Command to provide help info
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_message = (
        "🛠 **List of Commands**\n\n"
        "/start - Start the bot\n"
        "/connect - Get a random video chat link\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_message)

async def main():
    """Main function to run the bot."""
    # Initialize the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("help", help_command))

    # Run the bot with polling
    await application.run_polling()

if __name__ == "__main__":
    # Get the current event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
