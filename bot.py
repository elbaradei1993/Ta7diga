import random
import logging
import asyncio
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters

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

# Admin ID (Replace with your Telegram user ID)
ADMIN_ID = 123456789  # Replace with your actual Telegram ID

# List to hold users waiting for a video chat
waiting_users = []
active_users = set()
banned_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user_id = update.message.from_user.id
    if user_id in banned_users:
        await update.message.reply_text("🚫 لقد تم حظرك من استخدام هذا البوت.")
        return

    active_users.add(user_id)
    keyboard = [
        [InlineKeyboardButton("ابدأ محادثة جديدة", callback_data="connect")],
        [InlineKeyboardButton("كيفية الاستخدام", callback_data="howto")],
        [InlineKeyboardButton("سياسة الخصوصية", callback_data="privacy")],
        [InlineKeyboardButton("اتصل بنا", callback_data="contact")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "مرحبًا بك في تحديقة دردشة الفيديو العشوائية! 🎥\n\n"
        "اضغط على الزر أدناه لبدء محادثة جديدة أو معرفة المزيد عن الخدمة.",
        reply_markup=reply_markup
    )

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pair two users and provide a secure Jitsi video chat link."""
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    await query.answer()

    if user_id in banned_users:
        await query.message.reply_text("🚫 لقد تم حظرك من استخدام هذا البوت.")
        return

    if len(waiting_users) >= 1:
        matched_user = waiting_users.pop(0)
        video_chat_link = f"https://meet.jit.si/ta7diga-chat-{random.randint(1000,9999)}"
        
        await context.bot.send_message(chat_id=matched_user[0], text=f"🎥 تم إقرانك مع {user_name}! [انضم للمحادثة]({video_chat_link})")
        await context.bot.send_message(chat_id=user_id, text=f"🎥 تم إقرانك مع {matched_user[1]}! [انضم للمحادثة]({video_chat_link})")
    else:
        waiting_users.append((user_id, user_name))
        await query.message.reply_text("⏳ في انتظار مستخدم آخر للانضمام...")

async def howto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "🛠 **كيفية الاستخدام**\n"
        "1. اضغط على 'ابدأ محادثة جديدة'.\n"
        "2. انتظر حتى يتم العثور على مستخدم آخر.\n"
        "3. انقر على الرابط للانضمام إلى المحادثة."
    )

async def privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "🔒 **سياسة الخصوصية**\n"
        "- لا نقوم بتخزين بياناتك الشخصية.\n"
        "- جميع المحادثات مشفرة وآمنة."
    )

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📧 يمكنك الاتصال بنا عبر البريد الإلكتروني: sudanesegayassembly@gmail.com")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin panel for monitoring and banning users."""
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return
    
    keyboard = [
        [InlineKeyboardButton("عرض المستخدمين النشطين", callback_data="active_users")],
        [InlineKeyboardButton("حظر مستخدم", callback_data="ban_user")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("⚙️ **لوحة تحكم المسؤول**", reply_markup=reply_markup)

async def active_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    users = '\n'.join([str(user) for user in active_users]) or "لا يوجد مستخدمون نشطون حاليًا."
    await update.callback_query.message.reply_text(f"👥 المستخدمون النشطون:\n{users}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("🚨 الرجاء إرسال معرف المستخدم لحظره.")
    context.user_data["awaiting_ban"] = True

async def handle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID or "awaiting_ban" not in context.user_data:
        return
    
    try:
        user_to_ban = int(update.message.text)
        banned_users.add(user_to_ban)
        active_users.discard(user_to_ban)
        await update.message.reply_text(f"🚫 تم حظر المستخدم {user_to_ban}.")
    except ValueError:
        await update.message.reply_text("⚠️ يرجى إدخال معرف مستخدم صحيح.")
    
    del context.user_data["awaiting_ban"]

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(connect, pattern="connect"))
    application.add_handler(CallbackQueryHandler(howto, pattern="howto"))
    application.add_handler(CallbackQueryHandler(privacy, pattern="privacy"))
    application.add_handler(CallbackQueryHandler(contact, pattern="contact"))
    application.add_handler(CallbackQueryHandler(active_users_list, pattern="active_users"))
    application.add_handler(CallbackQueryHandler(ban_user, pattern="ban_user"))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^[0-9]+$"), handle_ban))
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
