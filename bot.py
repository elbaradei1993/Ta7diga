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
        photo TEXT,
        hiv_status TEXT,
        last_tested TEXT,
        relationship_status TEXT,
        pronouns TEXT
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
        [InlineKeyboardButton("🌍 استكشاف", callback_data="explore_mode")],
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

async def explore_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allow users to explore other locations."""
    query = update.callback_query
    await query.message.reply_text("📍 **أدخل اسم المدينة التي تريد البحث فيها:**")
    context.user_data["explore_mode"] = True

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle registration steps & explore mode."""
    user = update.message.from_user
    text = update.message.text
    step = context.user_data.get("register_step")
    
    if context.user_data.get("explore_mode"):
        await search_in_location(update, context, text)
        context.user_data["explore_mode"] = False
        return
    
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
        await update.message.reply_text("🔖 **اختر حالتك العاطفية:** (أعزب، مرتبط، متزوج)")
        context.user_data["register_step"] = "relationship_status"

    elif step == "relationship_status":
        cursor.execute("UPDATE users SET relationship_status=? WHERE id=?", (text, user.id))
        conn.commit()
        await update.message.reply_text("🏳️‍🌈 **أدخل ضمائرك:** (هو/هي/هم)")
        context.user_data["register_step"] = "pronouns"
    
    elif step == "pronouns":
        cursor.execute("UPDATE users SET pronouns=? WHERE id=?", (text, user.id))
        conn.commit()
        await update.message.reply_text("🩺 **أدخل حالة اختبار HIV الأخيرة:** (سلبي، إيجابي، غير معروف)")
        context.user_data["register_step"] = "hiv_status"
    
    elif step == "hiv_status":
        cursor.execute("UPDATE users SET hiv_status=? WHERE id=?", (text, user.id))
        conn.commit()
        await update.message.reply_text("📆 **متى أجريت آخر اختبار HIV؟** (مثال: يناير 2024)")
        context.user_data["register_step"] = "last_tested"
    
    elif step == "last_tested":
        cursor.execute("UPDATE users SET last_tested=? WHERE id=?", (text, user.id))
        conn.commit()
        await choose_type(update)

async def search_in_location(update: Update, context: ContextTypes.DEFAULT_TYPE, location: str) -> None:
    """Search users in a specific location."""
    cursor.execute("SELECT id, name, bio, type, photo FROM users WHERE location=?", (location,))
    users = cursor.fetchall()
    if not users:
        await update.message.reply_text("❌ لا يوجد مستخدمون في هذا الموقع.")
        return
    keyboard = [[InlineKeyboardButton(user[1], callback_data=f"profile_{user[0]}")] for user in users]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"🌍 المستخدمون في {location}:", reply_markup=reply_markup)

# Add other features like Taps, Tribes & Filters, Messaging, etc., as needed.

async def main():
    """Start bot."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(explore_mode, pattern="^explore_mode$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
