import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

# Your bot token
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Define command handler
async def start(update: Update, context):
    await update.message.reply_text("Hello! I am your random video chat bot!")

async def help_command(update: Update, context):
    await update.message.reply_text("Use /start to start the bot.")

# Main function to configure and run the bot
async def main():
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Run the bot
    logger.info("Bot is starting...")
    await application.run_polling()

# Entry point
if __name__ == "__main__":
    import asyncio

    # Use asyncio.run to handle the event loop correctly
    try:
        asyncio.run(main())
    except RuntimeError as e:
        logger.error(f"RuntimeError encountered: {e}")
