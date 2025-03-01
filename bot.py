import random
import logging
import asyncio
import nest_asyncio
import sqlite3
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Apply nest_asyncio for event loops
nest_asyncio.apply()

# Logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Database connection
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Create user profiles table
cursor.execute(
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        name TEXT,
        age INTEGER,
        bio TEXT,
        type TEXT,
        location TEXT,
        photo TEXT
    )"""
)
conn.commit()

ADMINS = [1796978458]  # Admin IDs

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command & enforce registration."""
    user = update.message.from_user
    cursor.execute("SELECT * FROM users WHERE id=?", (user.id,))
    result = cursor.fetchone()

    if not result:
        await update.message.reply_text("🔹 **يجب التسجيل أولًا لاستخدام البوت.**")
        await register(update, context)
        return

    keyboard = [
        [InlineKeyboardButton("🔍 حدّق", callback_data="search")],
        [InlineKeyboardButton("📝 تعديل ملفي", callback_data="edit_profile")],
        [InlineKeyboardButton("📍 تحديث موقعي", callback_data="update_location")],
        [InlineKeyboardButton("⚙ الإعدادات", callback_data="settings")],
    ]
    
    if user.id in ADMINS:
        keyboard.append([InlineKeyboardButton("🔧 لوحة الإدارة", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌟 **مرحبًا بك في تحديقة!** اختر من القائمة:", reply_markup=reply_markup)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Guide user through registration."""
    user = update.message.from_user
    cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user.id, user.username))
    conn.commit()
    
    await update.message.reply_text("✍ **أدخل اسمك الكامل:**")
    context.user_data["register_step"] = "name"

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle registration steps."""
    user = update.message.from_user
    text = update.message.text

    step = context.user_data.get("register_step")

    if step == "name":
        cursor.execute("UPDATE users SET name=? WHERE id=?", (text, user.id))
        conn.commit()
        await update.message.reply_text("📅 **أدخل عمرك:**")
        context.user_data["register_step"] = "age"

    elif step == "age":
        cursor.execute("UPDATE users SET age=? WHERE id=?", (text, user.id))
        conn.commit()
        await update.message.reply_text("📝 **أدخل نبذة عنك:**")
        context.user_data["register_step"] = "bio"

    elif step == "bio":
        cursor.execute("UPDATE users SET bio=? WHERE id=?", (text, user.id))
        conn.commit()
        await choose_type(update)

async def choose_type(update: Update) -> None:
    """Let users choose their type."""
    keyboard = [
        [InlineKeyboardButton("🌿 فرع", callback_data="type_branch"),
         InlineKeyboardButton("🍬 حلوة", callback_data="type_sweet")],
        [InlineKeyboardButton("🌾 برغل", callback_data="type_burghul"),
         InlineKeyboardButton("🎭 مارق", callback_data="type_mariq")],
        [InlineKeyboardButton("🎨 شادي الديكور", callback_data="type_shady"),
         InlineKeyboardButton("💃 بنوتي", callback_data="type_banoti")],
        [InlineKeyboardButton("✅ حفظ", callback_data="save_type")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔖 **اختر تصنيفك:** (يمكن اختيار أكثر من واحد)", reply_markup=reply_markup)

async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save user type selections."""
    query = update.callback_query
    user_id = query.from_user.id
    selected_type = query.data.replace("type_", "")

    cursor.execute("SELECT type FROM users WHERE id=?", (user_id,))
    user_type = cursor.fetchone()[0] or ""

    if selected_type in user_type:
        user_type = user_type.replace(selected_type, "")
    else:
        user_type += f"{selected_type},"

    cursor.execute("UPDATE users SET type=? WHERE id=?", (user_type, user_id))
    conn.commit()
    
    await query.answer("تم التحديث ✅")

async def save_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Finish registration process."""
    await update.callback_query.message.reply_text("📸 **أرسل صورتك الشخصية الآن:**")
    context.user_data["register_step"] = "photo"

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save user profile picture."""
    user = update.message.from_user
    file_id = update.message.photo[-1].file_id

    cursor.execute("UPDATE users SET photo=? WHERE id=?", (file_id, user.id))
    conn.commit()

    await update.message.reply_text("✅ **تم التسجيل بنجاح! يمكنك الآن البحث عن المستخدمين القريبين.**")
    await start(update, context)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Find nearby users."""
    query = update.callback_query
    user_id = query.from_user.id

    cursor.execute("SELECT location FROM users WHERE id=?", (user_id,))
    user_location = cursor.fetchone()[0]

    if not user_location:
        await query.answer("📍 قم بتحديث موقعك أولًا!")
        return

    cursor.execute("SELECT id, name, bio, type, photo FROM users WHERE id!=?", (user_id,))
    users = cursor.fetchall()

    if not users:
        await query.answer("❌ لا يوجد مستخدمون بالقرب منك حاليًا.")
        return

    keyboard = [[InlineKeyboardButton(user[1], callback_data=f"profile_{user[0]}")] for user in users]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("🔍 **المستخدمون القريبون:**", reply_markup=reply_markup)

async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display selected user profile."""
    query = update.callback_query
    user_id = int(query.data.split("_")[1])

    cursor.execute("SELECT name, bio, type, photo FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    profile_text = f"👤 {user[0]}\n📌 {user[1]}\n🔖 التصنيف: {user[2]}"
    
    buttons = [[InlineKeyboardButton("💬 رسالة", callback_data=f"message_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(buttons)

    await context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=user[3],
        caption=profile_text,
        reply_markup=reply_markup
    )

async def message_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle messaging between users."""
    query = update.callback_query
    recipient_id = int(query.data.split("_")[1])
    sender_id = query.from_user.id

    await context.bot.send_message(recipient_id, f"💌 لديك رسالة جديدة من {query.from_user.full_name}!")
    await query.answer("✅ تم إرسال طلب الدردشة!")

async def main():
    """Start bot."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(search, pattern="^search$"))
    app.add_handler(CallbackQueryHandler(view_profile, pattern="^profile_"))
    app.add_handler(CallbackQueryHandler(message_user, pattern="^message_"))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
