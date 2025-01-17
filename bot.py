from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store users waiting for a match
waiting_users = []

# Inline Keyboard Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("ابدأ دردشة الفيديو", callback_data="videochat"),
            InlineKeyboardButton("سياسة الخصوصية", callback_data="privacy"),
        ],
        [
            InlineKeyboardButton("المساعدة", callback_data="help"),
            InlineKeyboardButton("كيفية الاستخدام", callback_data="howto"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "مرحبًا! اختر خيارًا من القائمة أدناه:", reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "videochat":
        await start_video_chat(query, context)
    elif query.data == "privacy":
        await privacy_policy(query, context)
    elif query.data == "help":
        await help_ar(query, context)
    elif query.data == "howto":
        await how_to_use(query, context)

# Command Handlers
async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    privacy_message = (
        "🔒 **سياسة الخصوصية**\n\n"
        "خصوصيتك مهمة لنا. إليك كيفية تعاملنا مع بياناتك:\n\n"
        "1. نحن لا نخزن أي معلومات شخصية.\n"
        "2. نحن لا نشارك بياناتك مع أطراف ثالثة.\n"
        "3. جميع التفاعلات مع هذا البوت آمنة.\n\n"
        "إذا كانت لديك أي أسئلة، فلا تتردد في الاتصال بنا."
    )
    await update.callback_query.edit_message_text(privacy_message)

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
    await update.callback_query.edit_message_text(help_message)

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
    await update.callback_query.edit_message_text(howto_message)

async def start_video_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

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
        await update.callback_query.edit_message_text("⏳ في انتظار مستخدم آخر للانضمام...")

# Error Handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# Main Function
def main():
    # Use the provided bot token
    TOKEN = "7332555745:AAEGdPx1guRECMlIjlxTvms8Xx5EFDELelU"

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
