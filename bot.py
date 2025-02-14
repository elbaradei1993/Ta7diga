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
    """Send a welcome message when the command /start is issued and notify admins."""
    user = update.message.from_user
    keyboard = [
        [InlineKeyboardButton("ابدأ محادثة جديدة", callback_data="connect")],
        [InlineKeyboardButton("كيفية الاستخدام", callback_data="howto")],
        [InlineKeyboardButton("سياسة الخصوصية", callback_data="privacy")],
        [InlineKeyboardButton("📧 تواصل معنا", callback_data="contact")],
    ]
    if user.id in ADMINS:
        keyboard.append([InlineKeyboardButton("لوحة الإدارة", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحبًا بك في تحديقة! اختر أحد الخيارات أدناه:", reply_markup=reply_markup)

    # Notify admins about new user
    for admin_id in ADMINS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"📢 مستخدم جديد بدأ استخدام البوت: {user.first_name} (@{user.username}) - ID: {user.id}"
        )

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pair two users and provide a secure Jitsi video chat link, then notify admins."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    if user_id in banned_users:
        await query.edit_message_text("❌ تم حظرك من استخدام البوت.")
        return

    if len(waiting_users) >= 1:
        matched_user = waiting_users.pop(0)
        video_chat_link = f"https://meet.jit.si/ta7diga-chat-{random.randint(1000, 9999)}?start=true"

        # Notify both users about the match
        await context.bot.send_message(chat_id=matched_user[0], text=f"🎥 تم إقرانك مع {user_name}! [انضم للمحادثة]({video_chat_link})", parse_mode="Markdown")
        await context.bot.send_message(chat_id=user_id, text=f"🎥 تم إقرانك مع {matched_user[1]}! [انضم للمحادثة]({video_chat_link})", parse_mode="Markdown")

        # Notify admins about the match
        for admin_id in ADMINS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🔔 تم إقران مستخدمين في مكالمة فيديو:\n👤 {matched_user[1]} (ID: {matched_user[0]})\n👤 {user_name} (ID: {user_id})\n🔗 رابط المحادثة: {video_chat_link}"
            )
    else:
        waiting_users.append((user_id, user_name))
        await query.edit_message_text("⏳ في انتظار مستخدم آخر للانضمام...")

async def howto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔒 **سياسة الخصوصية**: لا نخزن أي بيانات شخصية وجميع الدردشات مجهولة.", parse_mode="Markdown")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMINS:
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول إلى لوحة الإدارة.")
        return

    keyboard = [
        [InlineKeyboardButton("📧 تواصل معنا", callback_data="contact")],
        [InlineKeyboardButton("📜 حظر مستخدم", callback_data="ban_user")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"📊 المستخدمون المتصلون الآن: {len(waiting_users)}\nاختر خيارًا أدناه:", reply_markup=reply_markup)

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    contact_link = "https://t.me/Felba"
    await query.edit_message_text(f"📧 [تواصل معنا عبر تيليجرام](<{contact_link}>)", parse_mode="Markdown")

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(connect, pattern="^connect$"))
    application.add_handler(CallbackQueryHandler(howto, pattern="^howto$"))
    application.add_handler(CallbackQueryHandler(privacy, pattern="^privacy$"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
