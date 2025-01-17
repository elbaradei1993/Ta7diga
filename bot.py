from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Custom keyboard with buttons in Arabic
    custom_keyboard = [
        ['/ابدأ', '/مساعدة'],
        ['/خصوصية', '/محادثة_فيديو'],
    ]
    
    # Set the reply markup to show buttons
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    # Send a message with the custom keyboard in Arabic
    await update.message.reply_text("مرحبًا! اختر أمرًا:", reply_markup=reply_markup)

# Add the command handler for the /start command
async def main():
    # Replace with your bot's API token
    TOKEN = "YOUR_BOT_API_TOKEN"
    application = Application.builder().token(TOKEN).build()

    # Add command handler
    application.add_handler(CommandHandler("start", start))

    # Start the bot
    print("الروبوت يعمل...")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
