from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Token for the new bot
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Define a command handler
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Hello! I am the تحديقة bot!')

# Set up the Application and handlers
async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handler
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    # Start polling for updates
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
