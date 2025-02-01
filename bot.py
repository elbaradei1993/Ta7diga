import random
import logging
import asyncio
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with inline buttons."""
    keyboard = [
        [InlineKeyboardButton("ابدأ محادثة جديدة 🚀", callback_data='connect')],
        [InlineKeyboardButton("كيفية الاستخدام 🛠", callback_data='howto')],
        [InlineKeyboardButton("سياسة الخصوصية 🔒", callback_data='privacy_policy')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "مرحبًا بك في تحديقة! 🎥\n\n"
        "ابدأ محادثة فيديو عشوائية الآن.\n\n"
        "💡 **كيفية الاستخدام؟**\n"
        "اضغط على أحد الأزرار أدناه:",
        reply_markup=reply_markup
    )

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the user a Jitsi video chat link."""
    query = update.callback_query
    await query.answer()
    
    video_chat_link = "https://meet.jit.si/ta7diga-chat"
    await query.message.reply_text(f"🎥 انقر هنا لبدء محادثة الفيديو: [اضغط هنا]({video_chat_link})", parse_mode="Markdown")

async def howto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send instructions."""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "🛠 **كيفية استخدام البوت**\n"
        "1. اضغط /connect لبدء البحث عن مستخدم آخر.\n"
        "2. سيتم إرسال رابط محادثة فيديو عشوائية.\n"
        "3. انقر على الرابط للانضمام.\n"
        "4. تأكد من منح إذن للكاميرا والميكروفون."
    )

async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send privacy policy information."""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "🔒 **سياسة الخصوصية**\n"
        "- البوت لا يخزن أي بيانات شخصية.\n"
        "- جميع المحادثات تتم عبر Jitsi ولا يتم تسجيلها.\n"
        "- لا تتم مشاركة بياناتك مع أطراف ثالثة."
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks."""
    query = update.callback_query
    await query.answer()

    if query.data == 'connect':
        await connect(update, context)
    elif query.data == 'howto':
        await howto(update, context)
    elif query.data == 'privacy_policy':
        await privacy_policy(update, context)

async def main():
    """Main function to run the bot."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
