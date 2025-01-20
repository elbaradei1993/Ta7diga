import random
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

# List to hold users waiting for a video chat
waiting_users = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text("مرحبًا! أنا تحديقة دردشة الفيديو العشوائية. 🎥\n\n"
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
                                   "إذا كانت لديك أي أسئلة، فلا تتردد في التواصل معنا. 😊")

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a random video chat for the user by pairing them with another user."""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name

    # Add user to the waiting list
    waiting_users.append((user_id, user_name))

    if len(waiting_users) >= 2:
        # Pair users
        user1, user2 = random.sample(waiting_users, 2)
        waiting_users.remove(user1)
        waiting_users.remove(user2)

        # Generate a unique video chat link using Jitsi
        room_name = f"random-chat-{user1[0]}-{user2[0]}"
        video_chat_link = f"https://meet.jit.si/{room_name}"

        # Send the link to both users
        await context.bot.send_message(
            chat_id=user1[0],
            text=f"🎥 لقد تم إقرانك مع {user2[1]}! اضغط هنا للانضمام إلى محادثة الفيديو: {video_chat_link}"
        )
        await context.bot.send_message(
            chat_id=user2[0],
            text=f"🎥 لقد تم إقرانك مع {user1[1]}! اضغط هنا للانضمام إلى محادثة الفيديو: {video_chat_link}"
        )
    else:
        await update.message.reply_text("⏳ في انتظار مستخدم آخر للانضمام...")
        

async def howto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send instructions on how to use the bot."""
    await update.message.reply_text(
        "🛠 **كيفية استخدام البوت**\n"
        "1. البوت سيفتح المتصفح.\n"
        "2. اختر مكان استخدامه (جوال أو كمبيوتر).\n"
        "3. لا حاجة لتنزيل 'Jitsi'.\n"
        "4. وافق على استخدام الكاميرا والميكروفون لبدء المحادثة.\n"
        "5. لا تستخدم رابط المحادثة القديم.\n"
        "6. اضغط /connect في كل مرة تريد بدء محادثة جديدة."
    )

async def main():
    """Main function to run the bot."""
    # Initialize the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("howto", howto))

    # Run the bot with polling
    await application.run_polling()

if __name__ == "__main__":
    # Get the current event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
