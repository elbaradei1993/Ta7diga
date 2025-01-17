from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging

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
    },
    "settings": {
        "ar": "⚙️ إعدادات البوت:\n\n- يمكنك تخصيص إعدادات البوت هنا.",
        "en": "⚙️ Bot Settings:\n\n- You can customize bot settings here.",
    },
    "contact_us": {
        "ar": "📞 اتصل بنا:\n\n- يمكنك إرسال استفساراتك أو تعليقاتك هنا.",
        "en": "📞 Contact Us:\n\n- You can send your inquiries or feedback here.",
    }
}

# Function to generate the main menu
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("المساعدة" if LANGUAGE == "ar" else "Help", callback_data="help")],
        [InlineKeyboardButton("كيفية الاستخدام" if LANGUAGE == "ar" else "How to Use", callback_data="how_to_use")],
        [InlineKeyboardButton("سياسة الخصوصية" if LANGUAGE == "ar" else "Privacy Policy", callback_data="privacy_policy")],
        [InlineKeyboardButton("\ud83d\udd8a\ufe0f ملاحظات" if LANGUAGE == "ar" else "\ud83d\udd8a\ufe0f Feedback", callback_data="feedback")],
        [InlineKeyboardButton("\ud83d\udcd6 عن البوت" if LANGUAGE == "ar" else "\ud83d\udcd6 About", callback_data="about")],
        [InlineKeyboardButton("إعدادات" if LANGUAGE == "ar" else "Settings", callback_data="settings")],  # New button
        [InlineKeyboardButton("اتصل بنا" if LANGUAGE == "ar" else "Contact Us", callback_data="contact_us")]  # New button
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(MESSAGES["welcome"][LANGUAGE], reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(MESSAGES["welcome"][LANGUAGE], reply_markup=reply_markup)

# Function to handle the help menu
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع" if LANGUAGE == "ar" else "Back", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        MESSAGES["help"][LANGUAGE],
        reply_markup=reply_markup,
    )

# Function to handle the how-to-use menu
async def how_to_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع" if LANGUAGE == "ar" else "Back", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        MESSAGES["how_to_use"][LANGUAGE],
        reply_markup=reply_markup,
    )

# Function to handle the privacy policy menu
async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع" if LANGUAGE == "ar" else "Back", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        MESSAGES["privacy_policy"][LANGUAGE],
        reply_markup=reply_markup,
    )

# Function to handle the feedback menu
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع" if LANGUAGE == "ar" else "Back", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        MESSAGES["feedback"][LANGUAGE],
        reply_markup=reply_markup,
    )

# Function to handle the about menu
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع" if LANGUAGE == "ar" else "Back", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        MESSAGES["about"][LANGUAGE],
        reply_markup=reply_markup,
    )

# Function to handle the settings menu
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع" if LANGUAGE == "ar" else "Back", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        MESSAGES["settings"][LANGUAGE],
        reply_markup=reply_markup,
    )

# Function to handle the contact us menu
async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع" if LANGUAGE == "ar" else "Back", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        MESSAGES["contact_us"][LANGUAGE],
        reply_markup=reply_markup,
    )

# Main function to set up the bot
def main():
    # Bot token
    TOKEN = "7332555745:AAEGdPx1guRECMlIjlxTvms8Xx5EFDELelU"

    application = Application.builder().token(TOKEN).build()

    # Command handler for the /start command
    application.add_handler(CommandHandler("start", main_menu))

    # Callback query handlers for menu buttons
    application.add_handler(CallbackQueryHandler(help_menu, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(how_to_use, pattern="^how_to_use$"))
    application.add_handler(CallbackQueryHandler(privacy_policy, pattern="^privacy_policy$"))
    application.add_handler(CallbackQueryHandler(feedback, pattern="^feedback$"))
    application.add_handler(CallbackQueryHandler(about, pattern="^about$"))
    application.add_handler(CallbackQueryHandler(settings, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(contact_us, pattern="^contact_us$"))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))

    # Start the bot
    print("البوت يعمل..." if LANGUAGE == "ar" else "The bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
