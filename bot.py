from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Function to generate the main menu
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("المساعدة", callback_data="help")],
        [InlineKeyboardButton("كيفية الاستخدام", callback_data="how_to_use")],
        [InlineKeyboardButton("سياسة الخصوصية", callback_data="privacy_policy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("\u2728 القائمة الرئيسية:", reply_markup=reply_markup)

# Function to handle the help menu
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "\u2753 قائمة المساعدة:\n\n- استخدم القائمة للتنقل.\n",
        reply_markup=reply_markup,
    )

# Function to handle the how-to-use menu
async def how_to_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "\ud83d\udd27 كيفية الاستخدام:\n\n1. استخدم الأزرار في القائمة.\n2. تنقل بسهولة عبر البوت.\n",
        reply_markup=reply_markup,
    )

# Function to handle the privacy policy menu
async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("الرجوع", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "\ud83d\udd12 سياسة الخصوصية:\n\nنحن نحترم خصوصيتك ولا نخزن أي معلومات شخصية.\n",
        reply_markup=reply_markup,
    )

# Function to handle the go-back action
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await main_menu(query, context)

# Main function to set up the bot
def main():
    # Replace with your bot's API token
    TOKEN = "7332555745:AAEGdPx1guRECMlIjlxTvms8Xx5EFDELelU"  # Replace with your actual bot token

    application = Application.builder().token(TOKEN).build()

    # Command handler for the /start command
    application.add_handler(CommandHandler("start", main_menu))

    # Callback query handlers for menu buttons
    application.add_handler(CallbackQueryHandler(help_menu, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(how_to_use, pattern="^how_to_use$"))
    application.add_handler(CallbackQueryHandler(privacy_policy, pattern="^privacy_policy$"))
    application.add_handler(CallbackQueryHandler(go_back, pattern="^main_menu$"))

    # Start the bot
    print("البوت يعمل...")
    application.run_polling()

if __name__ == "__main__":
    main()
