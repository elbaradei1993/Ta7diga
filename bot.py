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
        "/howto - كيفية استخدام البوت"
    )
    await update.message.reply_text(help_message)

# Command handler for /howto
async def how_to_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    howto_message = (
        "🛠 **كيفية استخدام البوت**:\n\n"
        "1. البوت سيفتح المتصفح.\n"
        "2. اختر مكان استخدامه (جوال أو كمبيوتر).\n"
        "3. لا حاجة لتنزيل 'Jitsi'.\n"
        "4. وافق على استخدام الكاميرا والميكروفون لبدء المحادثة.\n"
        "5. لا تستخدم رابط المحادثة القديم.\n"
        "6. اضغط /videochat في كل مرة تريد بدء محادثة جديدة."
    )
    await update.message.reply_text(howto_message)

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

        # Send the link to both users
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
    application.add_handler(CommandHandler("howto", how_to_use))
    application.add_handler(CommandHandler("videochat", start_video_chat))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()

from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import logging
import uuid

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Store users waiting for a match
waiting_users = []

# Create a Telegram Bot instance
bot = Bot(token='YOUR_TELEGRAM_BOT_TOKEN')

# Token mapping
tokens = {}

# Command handler for /start
def start(update, context):
    user_id = update.effective_user.id
    token = str(uuid.uuid4())
    tokens[token] = user_id
    link = f"https://your-github-pages-url.com?token={token}"
    update.message.reply_text(f"Please click the link to continue: {link}")

# Set up the dispatcher
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler('start', start))

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return 'OK'

@app.route('/start_video_chat', methods=['POST'])
def start_video_chat():
    data = request.get_json()
    token = data.get('token')
    user_id = tokens.get(token)
    if not user_id:
        return jsonify({'message': 'Invalid token.'}), 400
    user = bot.get_chat(user_id)
    user_name = user.first_name
    waiting_users.append({'user_id': user_id, 'user_name': user_name})
    
    if len(waiting_users) >= 2:
        user1 = waiting_users.pop(0)
        user2 = waiting_users.pop(0)
        room_name = f"random-chat-{user1['user_id']}-{user2['user_id']}"
        video_chat_link = f"https://meet.jit.si/{room_name}"
        
        bot.send_message(chat_id=user1['user_id'], text=f"🎥 لقد تم إقرانك مع {user2['user_name']}! اضغط هنا لبدء دردشة الفيديو: {video_chat_link}")
        bot.send_message(chat_id=user2['user_id'], text=f"🎥 لقد تم إقرانك مع {user1['user_name']}! اضغط هنا لبدء دردشة الفيديو: {video_chat_link}")
        
        return jsonify({'message': 'Paired with another user!'})
    else:
        return jsonify({'message': 'Waiting for another user...'})

if __name__ == "__main__":
    bot.set_webhook(url='https://your-railway-app-url.com/telegram_webhook')
    app.run()
