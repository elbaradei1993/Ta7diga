import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Your bot token
BOT_TOKEN = '7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak'

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define command handler
async def start(update: Update, context):
    await update.message.reply_text("Hello, I am your random video chat bot!")

async def help(update: Update, context):
    await update.message.reply_text("Use /start to start the bot.")

# Main function to run the bot
async def main():
    # Create the Application and pass it your bot's token
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))

    # Start polling
    await application.run_polling()

# Run the bot
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
