from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import random

# Store users waiting for a match
waiting_users = []

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا بك في تحديقة دردشة الفيديو العشوائية)

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
        "/videochat - بدء دردشة فيديو عشوائية"
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
        video_chat_link = f"https://meet.jit.si/{room_name}?jitsi_meet_external_api_id=0&config.startWithVideoMuted=true&config.startWithAudioMuted=true"

        # Send the link to both users with an Arabic permission message
        await context.bot.send_message(
            chat_id=user1[0],
            text=f"🎥 لقد تم إقرانك مع {user2[1]}! اضغط هنا لبدء دردشة الفيديو: {video_chat_link}\n\n"
                 "💡 **ملاحظة**: إذا لم تعمل الكاميرا أو الميكروفون، تأكد من منح الإذن في إعدادات المتصفح."
        )
        await context.bot.send_message(
            chat_id=user2[0],
            text=f"🎥 لقد تم إقرانك مع {user1[1]}! اضغط هنا لبدء دردشة الفيديو: {video_chat_link}\n\n"
                 "💡 **ملاحظة**: إذا لم تعمل الكاميرا أو الميكروفون، تأكد من منح الإذن في إعدادات المتصفح."
        )
    else:
        await update.message.reply_text("⏳ في انتظار مستخدم آخر للانضمام...")

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

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
