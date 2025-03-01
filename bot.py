import logging
import asyncio
import nest_asyncio
import aiosqlite  # Asynchronous SQLite library
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = "YOUR_BOT_TOKEN"

# Database connection
DATABASE = "users.db"

# Admin IDs
ADMINS = [1796978458]

# Initialize database
async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                age INTEGER,
                bio TEXT,
                type TEXT,
                location TEXT,
                photo TEXT,
                tribes TEXT
            )"""
        )
        await db.commit()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command & enforce registration."""
    try:
        user = update.message.from_user
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT * FROM users WHERE id=?", (user.id,))
            result = await cursor.fetchone()

        if not result:
            await update.message.reply_text("🔹 **يجب التسجيل أولًا لاستخدام البوت.**")
            await register(update, context)
            return

        keyboard = [
            [InlineKeyboardButton("🔍 حدّق", callback_data="search"),
             InlineKeyboardButton("👥 عرض المستخدمين", callback_data="show_users")],
            [InlineKeyboardButton("📝 تعديل ملفي", callback_data="edit_profile"),
             InlineKeyboardButton("📍 تحديث موقعي", callback_data="update_location")],
            [InlineKeyboardButton("🗑️ حذف الملف الشخصي", callback_data="delete_profile"),
             InlineKeyboardButton("⚙ الإعدادات", callback_data="settings")],
            [InlineKeyboardButton("🔙 الرجوع", callback_data="go_back")]
        ]
        
        if user.id in ADMINS:
            keyboard.append([InlineKeyboardButton("🔧 لوحة الإدارة", callback_data="admin_panel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🌟 **مرحبًا بك في تحديقة!** اختر من القائمة:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# Registration
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Guide user through registration."""
    user = update.message.from_user
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (id, username) VALUES (?, ?)",
            (user.id, user.username)
        )
        await db.commit()
    
    await update.message.reply_text("✍ **أدخل اسمك الكامل:**")
    context.user_data["register_step"] = "name"

# Handle messages during registration
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle registration steps."""
    try:
        user = update.message.from_user
        text = update.message.text
        step = context.user_data.get("register_step")

        if step == "name":
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("UPDATE users SET name=? WHERE id=?", (text, user.id))
                await db.commit()
            await update.message.reply_text("📅 **أدخل عمرك:**")
            context.user_data["register_step"] = "age"

        elif step == "age":
            if not text.isdigit():
                await update.message.reply_text("⚠️ **يجب إدخال رقم صحيح للعمر.**")
                return
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("UPDATE users SET age=? WHERE id=?", (int(text), user.id))
                await db.commit()
            await update.message.reply_text("📝 **أدخل نبذة عنك:**")
            context.user_data["register_step"] = "bio"

        elif step == "bio":
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("UPDATE users SET bio=? WHERE id=?", (text, user.id))
                await db.commit()
            await choose_type(update)
    except Exception as e:
        logger.error(f"Error in handle_messages: {e}")
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# Handle location
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user location updates."""
    try:
        user = update.message.from_user
        location = update.message.location
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "UPDATE users SET location=? WHERE id=?",
                (f"{location.latitude},{location.longitude}", user.id)
            )
            await db.commit()
        await update.message.reply_text("📍 **تم تحديث موقعك بنجاح!**")
    except Exception as e:
        logger.error(f"Error in handle_location: {e}")
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# Main function
async def main():
    """Start bot with updated handlers."""
    try:
        await init_db()  # Initialize database
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        app.add_handler(MessageHandler(filters.LOCATION, handle_location))
        app.add_handler(CallbackQueryHandler(delete_profile, pattern="^delete_profile$"))
        app.add_handler(CallbackQueryHandler(go_back, pattern="^go_back$"))

        # Stop any existing webhook
        await app.bot.delete_webhook()

        # Start polling
        await app.run_polling()
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())
