from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request
import logging
import asyncio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants for language support
LANGUAGE = "ar"  # Change to "en" for English
MESSAGES = {
    "welcome": {
        "ar": "\u2728 مرحبًا بك في البوت الخاص بنا! اختر من القائمة أدناه:",
        "en": "\u2728 Welcome to our bot! Choose from the menu below:",
    },
    "help": {
        "ar": "\u2753 قائمة المساعدة:\n\n- استخدم القائمة للتنقل.\n",
        "en": "\u2753 Help Menu:\n\n- Use the menu to navigate.\n",
    },
    "how_to_use": {
        "ar": "\ud83d\udd27 كيفية الاستخدام:\n\n1. استخدم الأزرار في القائمة.\n2. تنقل بسهولة عبر البوت.\n",
        "en": "\ud83d\udd27 How to use:\n\n1. Use the buttons in the menu.\n2. Navigate the bot easily.\n",
    },
    "privacy_policy": {
        "ar": "\ud83d\udd12 سياسة الخصوصية:\n\nنحن نحترم خصوصيتك ولا نخزن أي معلومات شخصية.\n",
        "en": "\ud83d\udd12 Privacy Policy:\n\nWe respect your privacy and do not store any personal information.\n",
    },
    "feedback": {
        "ar": "\ud83d\udd8a\ufe0f الرجاء إرسال ملاحظاتك لتحسين البوت:",
        "en": "\ud83d\udd8a\ufe0f Please send your feedback to improve the bot:",
    },
    "about": {
        "ar": "\ud83d\udcd6 عن البوت:\n\nهذا البوت تم تصميمه ليكون الأفضل في فئته!",
        "en": "\ud83d\udcd6 About the bot:\n\nThis bot is designed to be the best in its class!",
    }
}

# Flask app
app = Flask(__name__)

# Function to generate the main menu
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("المساعدة" if LANGUAGE == "ar" else "Help", callback_data="help")],
        [InlineKeyboardButton("كيفية الاستخدام" if LANGUAGE == "ar" else "How to Use", callback_data="how_to_use")],
        [InlineKeyboardButton("سياسة الخصوصية" if LANGUAGE == "ar" else "Privacy Policy", callback_data="privacy_policy")],
        [InlineKeyboardButton("\ud83d\udd8a\ufe0f ملاحظات" if LANGUAGE == "ar" else "\ud83d\udd8a\ufe0f Feedback", callback_data="feedback")],
        [InlineKeyboardButton("\ud83d\udcd6 عن البوت" if LANGUAGE == "ar" else "\ud83d\udcd6 About", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(MESSAGES["welcome"][LANGUAGE], reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(MESSAGES["welcome"][LANGUAGE], reply_markup=reply_markup)

# Function to handle callback data (menu actions)
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        message = MESSAGES["help"][LANGUAGE]
    elif query.data == "how_to_use":
        message = MESSAGES["how_to_use"][LANGUAGE]
    elif query.data == "privacy_policy":
        message = MESSAGES["privacy_policy"][LANGUAGE]
    elif query.data == "feedback":
        message = MESSAGES["feedback"][LANGUAGE]
    elif query.data == "about":
        message = MESSAGES["about"][LANGUAGE]
    else:
        message = MESSAGES["welcome"][LANGUAGE]
    
    keyboard = [
        [InlineKeyboardButton("الرجوع" if LANGUAGE == "ar" else "Back", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup)

# Flask route for webhook to handle updates
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json_str, application.bot)
    application.update_queue.put(update)  # Add the update to the queue
    return "OK", 200

# Main function to set up the bot and Flask server
async def main():
    TOKEN = "7332555745:AAHdJ6hUQbVmwLL_r3NE2erKHFQFn90vRoU"  # Replace with your new bot token

    global application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", main_menu))
    application.add_handler(CallbackQueryHandler(menu_callback))

    # Set webhook URL (replace with your actual server URL)
    await application.bot.set_webhook(url='https://yourdomain.com/webhook')

    # Start Flask app
    await asyncio.to_thread(app.run, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    asyncio.run(main())
