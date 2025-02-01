import random
import logging
import asyncio
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

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
ADMINS = [1796978458]  # Admin ID list (update with actual IDs)
banned_users = []  # List of banned users

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    keyboard = [
        [InlineKeyboardButton("ابدأ محادثة جديدة", callback_data="connect")],
        [InlineKeyboardButton("كيفية الاستخدام", callback_data="howto")],
        [InlineKeyboardButton("سياسة الخصوصية", callback_data="privacy")],
        [InlineKeyboardButton("📧 تواصل معنا", callback_data="contact")],  # Contact button for all users
    ]
    if update.message.from_user.id in ADMINS:
        keyboard.append([InlineKeyboardButton("لوحة الإدارة", callback_data="admin_panel")])  # Admin panel for admins
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحبًا بك في تحديقة! اختر أحد الخيارات أدناه:", reply_markup=reply_markup)

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pair two users and provide a secure Jitsi video chat link."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    # Check if the user is banned
    if user_id in banned_users:
        await query.edit_message_text("❌ تم حظرك من استخدام البوت.")
        return

    # If there is already a user in the waiting list, pair them and connect
    if len(waiting_users) >= 1:
        matched_user = waiting_users.pop(0)
        # Create a unique Jitsi meeting link for both users
        video_chat_link = f"https://meet.jit.si/ta7diga-chat-{random.randint(1000, 9999)}"

        # Notify both users about the match
        await context.bot.send_message(chat_id=matched_user[0], text=f"🎥 تم إقرانك مع {user_name}! [انضم للمحادثة]({video_chat_link})", parse_mode="Markdown")
        await context.bot.send_message(chat_id=user_id, text=f"🎥 تم إقرانك مع {matched_user[1]}! [انضم للمحادثة]({video_chat_link})", parse_mode="Markdown")
    else:
        # Add user to waiting list
        waiting_users.append((user_id, user_name))
        await query.edit_message_text("⏳ في انتظار مستخدم آخر للانضمام...")

async def howto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send instructions on how to use the bot."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛠 **كيفية استخدام البوت**\n"
        "1. البوت سيفتح المتصفح.\n"
        "2. لا حاجة لتنزيل 'Jitsi'.\n"
        "3. وافق على استخدام الكاميرا والميكروفون لبدء المحادثة.\n"
        "4. اضغط /connect في كل مرة تريد بدء محادثة جديدة.",
        parse_mode="Markdown"
    )

async def privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send privacy policy message."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔒 **سياسة الخصوصية**: لا نخزن أي بيانات شخصية وجميع الدردشات مجهولة.", parse_mode="Markdown")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin panel showing active users and options."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMINS:
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول إلى لوحة الإدارة.")
        return

    keyboard = [
        [InlineKeyboardButton("📧 تواصل معنا", callback_data="contact")],  # Contact button for admins in admin panel
        [InlineKeyboardButton("📜 حظر مستخدم", callback_data="ban_user")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"📊 المستخدمون المتصلون الآن: {len(waiting_users)}\nاختر خيارًا أدناه:", reply_markup=reply_markup)

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide contact method through Telegram chat."""
    query = update.callback_query
    await query.answer()
    contact_link = "https://t.me/Felba"
    await query.edit_message_text(f"📧 [تواصل معنا عبر تيليجرام](<{contact_link}>)", parse_mode="Markdown")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allow admins to ban a user."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMINS:
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    # Request user ID for banning
    await query.edit_message_text("🛑 أرسل لي معرف المستخدم (User ID) الذي ترغب في حظره.")
    user_input = await context.bot.get_updates()[-1].message.text
    banned_users.append(user_input)
    await query.edit_message_text(f"تم حظر المستخدم {user_input} بنجاح!")

async def main():
    """Main function to run the bot."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CallbackQueryHandler(connect, pattern="^connect$"))
    application.add_handler(CallbackQueryHandler(howto, pattern="^howto$"))
    application.add_handler(CallbackQueryHandler(privacy, pattern="^privacy$"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
    application.add_handler(CallbackQueryHandler(ban_user, pattern="^ban_user$"))

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
