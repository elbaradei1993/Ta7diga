import random
import logging
import asyncio
import nest_asyncio
import jwt
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Enable logging for debugging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Jitsi JWT authentication details (public Jitsi server)
JITSI_SECRET = "your-jitsi-secret"  # JWT secret (obtain or generate for your use case)
JITSI_APP_ID = "your-app-id"  # Your application ID (if applicable)
JITSI_DOMAIN = "meet.jit.si"  # Public Jitsi domain

# List to hold users waiting for a video chat
waiting_users = []
user_profiles = {}

def generate_jitsi_token(user_id, name):
    """Generate JWT token for Jitsi authentication."""
    # You can add randomness to the room name for unique sessions
    room_name = f"ta7diga-chat-{user_id}-{random.randint(1000, 9999)}"

    payload = {
        "context": {
            "user": {
                "avatar": "",
                "name": name,
                "email": f"{user_id}@ta7diga.com",
                "id": str(user_id)
            }
        },
        "aud": JITSI_APP_ID,
        "iss": JITSI_APP_ID,
        "sub": JITSI_DOMAIN,
        "room": room_name,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)  # Token valid for 2 hours
    }
    
    # Generate the JWT token
    token = jwt.encode(payload, JITSI_SECRET, algorithm="HS256")
    return token

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    logger.info(f"Start command received from {update.message.from_user.first_name} ({update.message.from_user.id})")
    
    # Create an inline keyboard button to open the mini app
    keyboard = [
        [InlineKeyboardButton("افتح تطبيق الدردشة العشوائية", web_app={"url": "https://ta7diga-mini-app-production.up.railway.app"})]  # Your app URL
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the welcome message with the button
    await update.message.reply_text(
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
        "إذا كانت لديك أي أسئلة، فلا تتردد في التواصل معنا. 😊", 
        reply_markup=reply_markup
    )

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pair two users and provide a secure Jitsi video chat link."""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    logger.info(f"Connect command received from {user_name} ({user_id})")

    if len(waiting_users) >= 1:
        # Pair with an existing user
        matched_user = waiting_users.pop(0)

        # Generate JWT tokens for both users
        token1 = generate_jitsi_token(matched_user[0], matched_user[1])
        token2 = generate_jitsi_token(user_id, user_name)

        # Jitsi Room URL with authentication
        video_chat_link1 = f"https://{JITSI_DOMAIN}/ta7diga-chat?jwt={token1}"
        video_chat_link2 = f"https://{JITSI_DOMAIN}/ta7diga-chat?jwt={token2}"

        # Notify users with their respective links
        await context.bot.send_message(
            chat_id=matched_user[0],
            text=f"🎥 تم إقرانك مع {user_name}! [انضم للمحادثة]({video_chat_link1})"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎥 تم إقرانك مع {matched_user[1]}! [انضم للمحادثة]({video_chat_link2})"
        )

        logger.info(f"Users {matched_user[1]} and {user_name} paired successfully.")

    else:
        # Add user to the waiting list
        waiting_users.append((user_id, user_name))
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
    logger.info("Bot is starting...")

    # Initialize the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("howto", howto))

    logger.info("Starting bot polling...")
    await application.run_polling()

if __name__ == "__main__":
    logger.info("Starting the main function...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
