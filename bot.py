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
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

# Bot token (updated as per your provided token)
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Command to start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    logger.info(f"/start command received from {update.message.from_user.id}")
    start_message = (
        "مرحبًا! أنا تحديقة دردشة الفيديو العشوائية. 🎥\n\n"
        "✨ **ماذا أقدم؟**\n"
        "- يمكنك بدء دردشة فيديو عشوائية مع مستخدمين آخرين.\n"
        "- الدردشة آمنة ومجهولة تمامًا.\n\n"
        "🛠 **كيفية الاستخدام**:\n"
        "1. أرسل /start لبدء التشغيل.\n"
        "2. أرسل /connect للبدء في البحث عن شريك دردشة.\n"
        "3. استمتع بمحادثة فيديو مع شخص جديد!\n\n"
        "🔒 **خصوصيتك مهمة**:\n"
        "- نحن لا نخزن أي معلومات شخصية.\n"
        "- جميع التفاعلات مع البوت آمنة ومشفرة.\n\n"
        "📝 **تعليمات الاستخدام**:\n"
        "- البوت سيفتح المتصفح.\n"
        "- اختر مكان استخدامه (جوال أو كمبيوتر).\n"
        "- لا حاجة لتنزيل 'Jitsi'.\n"
        "- وافق على استخدام الكاميرا والميكروفون لبدء المحادثة.\n"
        "- لا تستخدم رابط المحادثة القديم.\n"
        "- اضغط /connect في كل مرة تريد بدء محادثة جديدة.\n\n"
        "إذا كانت لديك أي أسئلة، فلا تتردد في التواصل معنا. 😊"
    )
    await update.message.reply_text(start_message)

# Command to connect users via random Jitsi video chat
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send a random Jitsi meet link."""
    logger.info(f"/connect command received from {update.message.from_user.id}")
    jitsi_base_url = "https://meet.jit.si/"
    random_meeting_id = f"Tahdiqa_{update.effective_user.id}"
    jitsi_link = jitsi_base_url + random_meeting_id
    connect_message = f"رابط دردشة الفيديو العشوائية الخاص بك: {jitsi_link}"
    await update.message.reply_text(connect_message)

# Command to provide help info
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"/help command received from {update.message.from_user.id}")
    help_message = (
        "🛠 **قائمة الأوامر**\n\n"
        "ابدأ استخدام البوت مع هذه الأوامر:\n\n"
        "/start - بدء التشغيل\n"
        "/connect - الحصول على رابط دردشة فيديو عشوائية\n"
        "/help - عرض هذه الرسالة"
    )
    await update.message.reply_text(help_message)

# Main function to run the bot
async def main():
    """Main function to run the bot."""
    # Initialize the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Delete any existing webhooks to avoid conflicts
    await application.bot.delete_webhook()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("help", help_command))

    # Run the bot with polling
    logger.info("Bot started and is polling for updates.")
    await application.run_polling()

if __name__ == "__main__":
    # Get the current event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
