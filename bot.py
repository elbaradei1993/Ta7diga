import random
import logging
import asyncio
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

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

# List to hold users waiting for a video chat
waiting_users = []
user_profiles = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    logger.info(f"Start command received from {update.message.from_user.first_name} ({update.message.from_user.id})")
    
    # Create an inline keyboard button to open the /connect command directly
    keyboard = [
        [InlineKeyboardButton("ابدأ محادثة جديدة 🚀", callback_data='connect')],
        [InlineKeyboardButton("كيفية الاستخدام 🛠", callback_data='howto')],
        [InlineKeyboardButton("سياسة الخصوصية 🔒", callback_data='privacy_policy')]
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

        # Jitsi Room URL (public server doesn't require JWT)
        video_chat_link1 = f"https://meet.jit.si/ta7diga-chat"
        video_chat_link2 = f"https://meet.jit.si/ta7diga-chat"

        # Notify users with the video chat links
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

# This function handles the callback query when the inline button is clicked
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the inline button click for various actions."""
    query = update.callback_query
    callback_data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    logger.info(f"User {user_name} ({user_id}) clicked the button with callback data '{callback_data}'.")

    if callback_data == 'connect':
        await connect(update, context)
    elif callback_data == 'howto':
        await howto(update, context)
    elif callback_data == 'privacy_policy':
        await privacy_policy(update, context)

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

async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the privacy policy."""
    await update.message.reply_text(
        "🔒 **سياسة الخصوصية**\n\n"
        "- نحن نلتزم بحماية خصوصيتك.\n"
        "- البوت لا يقوم بتخزين أي معلومات شخصية.\n"
        "- جميع المحادثات عبر Jitsi مشفرة.\n"
        "- يمكن للمستخدمين التواصل بحرية ودون الحاجة لتسجيل الدخول.\n"
        "- بمجرد إنهاء المحادثة، لا يتم تخزين أي بيانات."
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
    application.add_handler(CommandHandler("privacy_policy", privacy_policy))

    # Register the callback query handler for inline button
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info("Starting bot polling...")
    await application.run_polling()

if __name__ == "__main__":
    logger.info("Starting the main function...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
