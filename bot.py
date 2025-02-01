import random
import logging
import asyncio
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Queue for users waiting to be paired
waiting_users = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with inline buttons."""
    keyboard = [
        [InlineKeyboardButton("ابدأ محادثة جديدة 🚀", callback_data='connect')],
        [InlineKeyboardButton("كيفية الاستخدام 🛠", callback_data='howto')],
        [InlineKeyboardButton("سياسة الخصوصية 🔒", callback_data='privacy_policy')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "مرحبًا بك في تحديقة! 🎥\n\n"
        "ابدأ محادثة فيديو عشوائية الآن.\n\n"
        "💡 **كيفية الاستخدام؟**\n"
        "اضغط على أحد الأزرار أدناه:",
        reply_markup=reply_markup
    )

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Match users before sending a Jitsi link."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check if a user is already waiting
    if waiting_users:
        # Pair the two users
        partner_id = waiting_users.pop(0)
        jitsi_link = f"https://meet.jit.si/ta7diga-{random.randint(1000, 9999)}"

        # Notify both users
        await context.bot.send_message(partner_id, f"🎥 تم العثور على شريك! انقر هنا للانضمام: [اضغط هنا]({jitsi_link})", parse_mode="Markdown")
        await context.bot.send_message(user_id, f"🎥 تم العثور على شريك! انقر هنا للانضمام: [اضغط هنا]({jitsi_link})", parse_mode="Markdown")
        
    else:
        # Add user to queue and tell them to wait
        waiting_users.append(user_id)
        await query.answer()
        await query.message.reply_text("⌛ جاري البحث عن شريك لك... الرجاء الانتظار.")

async def howto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send instructions."""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "🛠 **كيفية استخدام البوت**\n"
        "1. اضغط 'ابدأ محادثة جديدة' للانضمام إلى قائمة الانتظار.\n"
        "2. سيتم البحث عن مستخدم آخر تلقائيًا.\n"
        "3. عند العثور على شريك، سيتم إرسال رابط محادثة فيديو.\n"
        "4. انقر على الرابط للانضمام.\n"
        "5. تأكد من منح إذن للكاميرا والميكروفون."
    )

async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send privacy policy information."""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "🔒 **سياسة الخصوصية**\n"
        "- البوت لا يخزن أي بيانات شخصية.\n"
        "- جميع المحادثات تتم عبر Jitsi ولا يتم تسجيلها.\n"
        "- لا تتم مشاركة بياناتك مع أطراف ثالثة."
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks."""
    query = update.callback_query
    await query.answer()

    if query.data == 'connect':
        await connect(update, context)
    elif query.data == 'howto':
        await howto(update, context)
    elif query.data == 'privacy_policy':
        await privacy_policy(update, context)

async def main():
    """Main function to run the bot."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
