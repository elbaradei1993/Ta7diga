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

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    start_message = (
        "مرحبًا! أنا تحديقة دردشة الفيديو العشوائية. 🎥\n\n"
        "✨ **ماذا أقدم؟**\n"
        "- يمكنك بدء دردشة فيديو عشوائية مع مستخدمين آخرين.\n"
        "- الدردشة آمنة ومجهولة تمامًا.\n\n"
        "🛠 **كيفية الاستخدام**:\n"
        "1. أرسل /start لبدء التشغيل.\n"
        "2. أرسل /videochat للبدء في البحث عن شريك دردشة.\n"
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
        "- اضغط /videochat في كل مرة تريد بدء محادثة جديدة.\n\n"
        "إذا كانت لديك أي أسئلة، فلا تتردد في التواصل معنا. 😊"
    )
    await update.message.reply_text(start_message)

# Command handler for /connect (video chat link generation)
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send a random Jitsi meet link."""
    jitsi_base_url = "https://meet.jit.si/"
    random_meeting_id = f"Tahdiqa_{update.effective_user.id}"
    jitsi_link = jitsi_base_url + random_meeting_id
    await update.message.reply_text(f"رابط دردشة الفيديو العشوائي الخاص بك: {jitsi_link}")

# Command handler for /help
async def help_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "🛠 **قائمة الأوامر**\n\n"
        "ابدأ استخدام البوت مع هذه الأوامر:\n\n"
        "/start - بدء التشغيل\n"
        "/connect - بدء دردشة فيديو عشوائية\n"
        "/help - عرض هذه الرسالة"
    )
    await update.message.reply_text(help_message)

# Main function to run the bot
async def main():
    """Main function to run the bot."""
    # Initialize the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("help", help_ar))

    # Run the bot with polling
    await application.run_polling()

if __name__ == "__main__":
    # Get the current event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
