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
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Command for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
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

# Command for /connect
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send a random Jitsi meet link."""
    jitsi_base_url = "https://meet.jit.si/"
    random_meeting_id = f"Tahdiqa_{update.effective_user.id}"
    jitsi_link = jitsi_base_url + random_meeting_id
    await update.message.reply_text(f"Your random video chat link: {jitsi_link}")

# Command for /howto
async def how_to_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send how-to instructions for using the bot."""
    howto_message = (
        "🛠 **كيفية استخدام البوت**\n\n"
        "1. البوت سيفتح المتصفح.\n"
        "2. اختر مكان استخدامه (جوال أو كمبيوتر).\n"
        "3. لا حاجة لتنزيل 'Jitsi'.\n"
        "4. وافق على استخدام الكاميرا والميكروفون لبدء المحادثة.\n"
        "5. لا تستخدم رابط المحادثة القديم.\n"
        "6. اضغط /connect في كل مرة تريد بدء محادثة جديدة."
    )
    await update.message.reply_text(howto_message)

async def main():
    """Main function to run the bot."""
    # Initialize the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("howto", how_to_use))

    # Run the bot with polling
    await application.run_polling()

if __name__ == "__main__":
    # Get the current event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
