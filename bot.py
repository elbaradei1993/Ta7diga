import random
import logging
import asyncio
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import firebase_admin
from firebase_admin import credentials, db

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Enable logging for debugging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Firebase Admin SDK credentials setup
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": "ta7diga",
    "private_key_id": "71d893e61659b679b0268d0be5869240a7d0185e",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCbz+2hXxU7j8w0\n5lR2zIjZdJjhEceztibuITpNVJbVyEwv1wTEKlS+cHW3AmootWNSZVGjI5upWP89\ny8hT1RwIzBx2PnhXQs/z75jgyv14KUZ/9aeAAxTS6Qs1LYRR3vxGA3s4OtyJFn6i\nHc/3+1Qs2ewzgN/Y01UDsxM9mbrQRq6EJQgr959j3vgJrbz1kH8wAUce5iDFPe47\nAksB9xDVoY8lo7uAxw6eZ5w7fPLud7qVquD/9kAJQDF2zQpRdJW2qoso5M9PWbD/\nqitOBGmgVOVe9eDwI4SUInZMv7LVArTxAT4d3ONjHFbGeceXqMR9DIcznxWApwbs\nR+JFcnAbAgMBAAECggEALMHOL1gaR8k3Lgzpv1RijSB+l8xdMqTEywuVbUg6qb9H\nD0jzEAxe2nOAhOj3KKluFemPyU59tOghLZWffmFNk8NZ+6dXNy20gYxWPGBi7gTh\nQPmGO3HnJeyWcRiZlVD543y1hQH3fpONHbF1n3S9CcMxo9vFsUmHdrAWe0/xB0mL\nq0qwkOk3a51MNIAaZ+ZbL8fTTs88ypjj/gkCxKjg4u7sY1fXzN9D6aeOTa6CX/tL\nr6qJFzHaRBhYgmznPJOyJk6AWUIRMJ9H9Djb0Ht0lK+hkUcMPMtrXSwSNJjrWaRk\nNSL30X8hESl++Zxz+hyrCDr+PYnZu3PtYXcfLq9cKQKBgQDMbU3G8lTa4Ye1qbl/\nsABUm3xA6qhpb6F/biWviu5FolkZ+WvH3C0YiBAVBfa+DSw7FfIDFA9ZWOGx+X9Q\noHiuUsYUd86AaiPclaADOHLOvULAH6YlUHaspiWC1KGC+hsGd0vypIzsFvA8kC1M\nvLsis0NAkAO4quSP1jyBugia+QKBgQDDHuSjQYMo9tEF/H1o0jWsZaik/iivQJeM\nuZQ0T4dLO8VpIKgY5LKJbc7x01Mdrla27xyi2lqQeYSLn1zImHyxYigUmEqRdvCX\ncCsa/bFbWj70xsPrP4K9eOz19laUuMF1PtSslPBHXKxcv5yBnp3Y4J/sTaYn/lzh\nGGPhpu+0swKBgAhnPdk9wOs2diOrlGqBS6Iuug7ZFo8u/Y6FcpsitOS75bnBnQKc\nNGZbwX17v0bUt8q9/jLOMktT8gMk5GzmC8/uqyHQQvbYZhz9MZSwT1fcQ9At/OBv\nzFEQi14za2g867t6T+7rgLd7wehbbOFIqNCmWc9fnCeNLtQS1G3ovc3RAoGBAMFT\nTKpM8M2XrwbFYuSG0tNbbjr78AekcgPmo+conR53vGMrDiKMBjGQcSi9f267HAPo\n6nCY9H6NSDymy2GdZH7EiH3PXqK+PCdv5eW6Uw32XsZcYiYmKT3eILqbNrHoVRX8\nCPBuKZwrQEQtPb5YEIGgHhQd43Fg31nPtrcPlhVtAoGASdbhNslraeeZOZbkBnoG\no+D1za1I/06ghYjpm3qwl9MKPChrukSMY2EuElvlvpBk1ozTqYpLyxgrAbDvE7rv\nfEmjR+gjr4JSTAC6kWjZOuTTNpfp7F3upqGJGL+9b0DWogK4GA0nD3TAtwzhJtuz\nKDH9getAA4yz0jqS8IlPd+4=\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-fbsvc@ta7diga.iam.gserviceaccount.com",
    "client_id": "107807975434460440132",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40ta7diga.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
})

# Initialize Firebase app
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ta7diga.firebaseio.com'  # Replace with your Firebase Realtime Database URL
})

# Function to write to Firebase Realtime Database
def write_to_firebase(data):
    ref = db.reference('/users')
    ref.push(data)

# Function to read from Firebase
def read_from_firebase():
    ref = db.reference('/users')
    data = ref.get()
    return data

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
        [InlineKeyboardButton("📧 تواصل معنا", callback_data="contact")],
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
        video_chat_link = f"https://meet.jit.si/ta7diga-chat-{random.randint(1000, 9999)}?start=true"

        # Notify both users about the match
        await context.bot.send_message(chat_id=matched_user[0], text=f"🎥 تم إقرانك مع {user_name}! [انضم للمحادثة]({video_chat_link})", parse_mode="Markdown")
        await context.bot.send_message(chat_id=user_id, text=f"🎥 تم إقرانك مع {matched_user[1]}! [انضم للمحادثة]({video_chat_link})", parse_mode="Markdown")

        # Log the user connection to Firebase
        write_to_firebase({"user1_id": matched_user[0], "user2_id": user_id, "video_chat_link": video_chat_link})
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
        [InlineKeyboardButton("📧 تواصل معنا", callback_data="contact")],
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
