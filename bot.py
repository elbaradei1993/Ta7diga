import random
import logging
import asyncio
import nest_asyncio
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

# List to hold users waiting for a video chat
waiting_users = []
user_profiles = {}

# Admin Panel Data
admin_users = [1796978458]  # Replace with actual Telegram user IDs of admins
banned_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    logger.info(f"Start command received from {update.message.from_user.first_name} ({update.message.from_user.id})")
    
    keyboard = [
        [InlineKeyboardButton("ابدأ محادثة جديدة", callback_data="connect")],
        [InlineKeyboardButton("كيفية الاستخدام", callback_data="howto")],
        [InlineKeyboardButton("سياسة الخصوصية", callback_data="privacy")]
    ]
    if update.message.from_user.id in admin_users:
        keyboard.append([InlineKeyboardButton("لوحة التحكم الإدارية", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "مرحبًا! أنا تحديقة دردشة الفيديو العشوائية. 🎥\n\n"
        "✨ **ماذا أقدم؟**\n"
        "- يمكنك بدء دردشة فيديو عشوائية مع مستخدمين آخرين.\n"
        "- الدردشة آمنة ومجهولة تمامًا.\n\n",
        reply_markup=reply_markup
    )

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pair two users and provide a secure Jitsi video chat link."""
    user_id = update.callback_query.from_user.id
    user_name = update.callback_query.from_user.first_name
    logger.info(f"Connect command received from {user_name} ({user_id})")
    
    if user_id in banned_users:
        await update.callback_query.answer("❌ تم حظرك من استخدام البوت.", show_alert=True)
        return
    
    if len(waiting_users) >= 1:
        matched_user = waiting_users.pop(0)
        video_chat_link = f"https://meet.jit.si/ta7diga-chat"

        await context.bot.send_message(chat_id=matched_user[0], text=f"🎥 تم إقرانك مع {user_name}! [انضم للمحادثة]({video_chat_link})")
        await context.bot.send_message(chat_id=user_id, text=f"🎥 تم إقرانك مع {matched_user[1]}! [انضم للمحادثة]({video_chat_link})")
    else:
        waiting_users.append((user_id, user_name))
        await update.callback_query.answer("⏳ في انتظار مستخدم آخر للانضمام...", show_alert=True)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin panel to view active users and manage bans."""
    user_id = update.callback_query.from_user.id
    if user_id not in admin_users:
        await update.callback_query.answer("❌ ليس لديك صلاحية الوصول.", show_alert=True)
        return
    
    keyboard = [[InlineKeyboardButton("📋 المستخدمون النشطون", callback_data="active_users")],
                [InlineKeyboardButton("🚫 إدارة الحظر", callback_data="ban_users")],
                [InlineKeyboardButton("✉️ تواصل معنا", url="mailto:sudanesegayassembly@gmail.com")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text("🔧 **لوحة التحكم الإدارية**", reply_markup=reply_markup)

async def active_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the number of active users."""
    await update.callback_query.answer(f"👥 عدد المستخدمين النشطين حاليًا: {len(waiting_users)}", show_alert=True)

async def ban_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ban a user manually (Admin only)."""
    # Implement manual banning logic here
    await update.callback_query.answer("🚫 ميزة الحظر قيد التطوير.", show_alert=True)

async def privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send privacy policy."""
    await update.callback_query.message.reply_text("🔒 سياسة الخصوصية: لا نقوم بتخزين أي بيانات شخصية.")

async def howto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send usage instructions."""
    await update.callback_query.message.reply_text("📖 كيفية الاستخدام: اضغط على 'ابدأ محادثة جديدة' لبدء دردشة فيديو عشوائية.")

async def main():
    """Main function to run the bot."""
    logger.info("Bot is starting...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("howto", howto))
    application.add_handler(CommandHandler("privacy", privacy))
    application.add_handler(CommandHandler("admin_panel", admin_panel))
    application.add_handler(CommandHandler("active_users", active_users))
    application.add_handler(CommandHandler("ban_users", ban_users))
    
    logger.info("Starting bot polling...")
    await application.run_polling()

if __name__ == "__main__":
    logger.info("Starting the main function...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
