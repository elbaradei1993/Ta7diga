import random
import logging
import asyncio
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Enable logging for better debugging
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
    
    # Create an inline keyboard button to open the mini app
    keyboard = [
        [InlineKeyboardButton("افتح تطبيق الدردشة العشوائية", web_app={"url": "https://ta7diga-mini-app-production.up.railway.app"})]  # Your app URL
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the welcome message with the button
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
                                   "إذا كانت لديك أي أسئلة، فلا تتردد في التواصل معنا. 😊", 
                                   reply_markup=reply_markup)

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a random video chat for the user by pairing them with another user."""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    logger.info(f"Connect command received from {user_name} ({user_id})")

    # Check if the user is already in the waiting list
    for u in waiting_users:
        if u[0] == user_id:
            await update.message.reply_text("⏳ أنت بالفعل في قائمة الانتظار، يرجى الانتظار لمطابقتك مع شخص آخر.")
            return

    # Add user to the waiting list
    waiting_users.append((user_id, user_name))
    logger.info(f"User {user_name} added to the waiting list. Total users in queue: {len(waiting_users)}")

    if len(waiting_users) >= 2:
        # Pair the first two users in the queue
        user1 = waiting_users.pop(0)
        user2 = waiting_users.pop(0)

        # Use a fixed Jitsi room name to avoid authentication issues
        room_name = "ta7diga-chat"
        video_chat_link = f"https://meet.jit.si/{room_name}"

        # Notify both users
        await context.bot.send_message(
            chat_id=user1[0],
            text=f"🎥 لقد تم إقرانك مع {user2[1]}! اضغط هنا للانضمام إلى محادثة الفيديو: {video_chat_link}"
        )
        await context.bot.send_message(
            chat_id=user2[0],
            text=f"🎥 لقد تم إقرانك مع {user1[1]}! اضغط هنا للانضمام إلى محادثة الفيديو: {video_chat_link}"
        )
        logger.info(f"Users {user1[1]} and {user2[1]} paired successfully.")
    else:
        # Notify the user to wait for another user
        await update.message.reply_text("⏳ في انتظار مستخدم آخر للانضمام...")
        logger.info(f"User {user_name} is waiting for another user to join.")

async def howto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send instructions on how to use the bot."""
    logger.info(f"How-to command received from {update.message.from_user.first_name} ({update.message.from_user.id})")
    await update.message.reply_text(
        "🛠 **كيفية استخدام البوت**\n"
        "1. البوت سيفتح المتصفح.\n"
        "2. اختر مكان استخدامه (جوال أو كمبيوتر).\n"
        "3. لا حاجة لتنزيل 'Jitsi'.\n"
        "4. وافق على استخدام الكاميرا والميكروفون لبدء المحادثة.\n"
        "5. لا تستخدم رابط المحادثة القديم.\n"
        "6. اضغط /connect في كل مرة تريد بدء محادثة جديدة."
    )

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allow users to edit their profile (name or photo)."""
    user_id = update.message.from_user.id

    # Check if the user has a profile
    if user_id not in user_profiles:
        user_profiles[user_id] = {"name": update.message.from_user.first_name, "photo": None}

    # Send a message asking the user what they want to update
    await update.message.reply_text("🔧 ماذا ترغب في تحديثه؟\n"
                                   "1. تغيير الاسم\n"
                                   "2. رفع صورة الملف الشخصي\n"
                                   "رد على هذه الرسالة مع الرقم الخاص باختيارك.")

async def handle_profile_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the profile updates (name or photo)."""
    user_id = update.message.from_user.id
    user_choice = update.message.text.strip()

    if user_choice == "1":  # Change Name
        # Prompt the user to enter the new name
        await update.message.reply_text("من فضلك أدخل اسمك الجديد:")
        # Store the new name in a variable or prompt for further input.
        user_profiles[user_id]["name"] = update.message.text
        await update.message.reply_text(f"تم تحديث اسمك إلى {update.message.text}.")
        
    elif user_choice == "2":  # Upload Profile Picture
        # Handle the logic for uploading and saving profile pictures
        await update.message.reply_text("من فضلك أرسل صورة الملف الشخصي الجديدة.")
        # Process and store the photo from the user's input.
        user_profiles[user_id]["photo"] = update.message.photo[-1].file_id
        await update.message.reply_text("تم تحديث صورة الملف الشخصي!")

async def main():
    """Main function to run the bot."""
    logger.info("Bot is starting...")

    # Initialize the bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("howto", howto))
    application.add_handler(CommandHandler("editprofile", edit_profile))

    # Add a message handler to process user replies for profile updates
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_update))

    logger.info("Starting bot polling...")
    # Run the bot with polling
    await application.run_polling()

if __name__ == "__main__":
    logger.info("Starting the main function...")
    # Get the current event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
