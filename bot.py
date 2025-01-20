import logging
from telegram import Update
from telegram.ext import Application, CommandHandler
import asyncio

# Your bot token
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Define command handlers
async def start(update: Update, context):
    await update.message.reply_text("Hello! I am your random video chat bot!")

async def help_command(update: Update, context):
    await update.message.reply_text("Use /start to start the bot.")

# Main bot setup function
async def run_bot():
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Start the bot
    logger.info("Bot is starting...")
    await application.run_polling()

# Entry point
if __name__ == "__main__":
    try:
        # Check for an already running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the bot within the loop
        loop.run_until_complete(run_bot())
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
