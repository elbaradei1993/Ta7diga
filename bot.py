from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import random
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store users waiting for a match
waiting_users = []

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا! البوت يعمل الآن. 🎉")

# Command handler for /privacy
async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    privacy_message = (
        "🔒 **سياسة الخصوصية**\n\n"
        "خصوصيتك مهمة لنا. إليك كيفية تعاملنا مع بياناتك:\n\n"
        "1. نحن لا نخزن أي معلومات شخصية.\n"
        "2. نحن لا نشارك بياناتك مع أطراف ثالثة.\n"
        "3. جميع التفاعلات مع هذا البوت آمنة.\n\n"
        "إذا كانت لديك أي أسئلة، فلا تتردد في الاتصال بنا."
    )
    await update.message.reply_text(privacy_message)

# Command handler for /help
async def help_ar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "🛠 **قائمة الأوامر**\n\n"
        "ابدأ استخدام البوت مع هذه الأوامر:\n\n"
        "/start - بدء التشغيل\n"
        "/privacy - عرض سياسة الخصوصية\n"
        "/help - عرض هذه الرسالة\n"
        "/videochat - بدء دردشة فيديو عشوائية\n"
        "/skip - تخطي المستخدم الحالي\n"
        "/report - الإبلاغ عن سلوك غير لائق\n"
        "/chat - بدء دردشة نصية"
    )
    await update.message.reply_text(help_message)

# Command handler for /videochat
async def start_video_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name

    # Add the user to the waiting list
    waiting_users.append((user_id, user_name))

    if len(waiting_users) >= 2:
        # Pair two random users
        user1, user2 = random.sample(waiting_users, 2)
        waiting_users.remove(user1)
        waiting_users.remove(user2)

        # Generate a unique video chat link using Jitsi Meet
        room_name = f"random-chat-{user1[0]}-{user2[0]}"
        video_chat_link = f"https://meet.jit.si/{room_name}"

        # Send the link to both users
        await context.bot.send_message(
            chat_id=user1[0],
            text=f"🎥 لقد تم إقرانك مع {user2[1]}! اضغط هنا لبدء دردشة الفيديو: {video_chat_link}"
        )
        await context.bot.send_message(
            chat_id=user2[0],
            text=f"🎥 لقد تم إقرانك مع {user1[1]}! اضغط هنا لبدء دردشة الفيديو: {video_chat_link}"
        )
    else:
        await update.message.reply_text("⏳ في انتظار مستخدم آخر للانضمام...")

# Command handler for /skip
async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if (user_id, _) in waiting_users:
        waiting_users.remove((user_id, _))
        await update.message.reply_text("تم تخطي المستخدم. البحث عن مستخدم جديد...")
    else:
        await update.message.reply_text("لا يوجد مستخدم لتخطيه.")

# Command handler for /report
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إرسال تقريرك. سنقوم بمراجعته قريبًا.")

# Command handler for /chat
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if len(waiting_users) >= 2:
        user1, user2 = random.sample(waiting_users, 2)
        await context.bot.send_message(chat_id=user1[0], text=f"💬 يمكنك الدردشة مع {user2[1]}.")
        await context.bot.send_message(chat_id=user2[0], text=f"💬 يمكنك الدردشة مع {user1[1]}.")
    else:
        await update.message.reply_text("⏳ في انتظار مستخدم آخر للانضمام...")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

def main():
    # Replace with your bot's API token
    TOKEN = "7332555745:AAEGdPx1guRECMlIjlxTvms8Xx5EFDELelU"

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("privacy", privacy_policy))
    application.add_handler(CommandHandler("help", help_ar))
    application.add_handler(CommandHandler("videochat", start_video_chat))
    application.add_handler(CommandHandler("skip", skip))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("chat", chat))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()