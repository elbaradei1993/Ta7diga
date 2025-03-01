import logging
import asyncio
import nest_asyncio
import aiosqlite
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
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

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
        await db.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user.id, user.username))
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
            # Validate age input
            try:
                age = int(text)
                if age < 1 or age > 120:
                    await update.message.reply_text("❌ العمر غير صالح. يرجى إدخال عمر بين 1 و 120.")
                    return
            except ValueError:
                await update.message.reply_text("❌ العمر غير صالح. يرجى إدخال رقم.")
                return

            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("UPDATE users SET age=? WHERE id=?", (age, user.id))
                await db.commit()
            await update.message.reply_text("📝 **أدخل نبذة عنك:**")
            context.user_data["register_step"] = "bio"

        elif step == "bio":
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("UPDATE users SET bio=? WHERE id=?", (text, user.id))
                await db.commit()
            await choose_type(update)
            context.user_data["register_step"] = None  # Clear the step after completion

    except Exception as e:
        logger.error(f"Error in handle_messages: {e}")
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# Choose type
async def choose_type(update: Update) -> None:
    """Let users choose their type (تصنيفك)."""
    try:
        keyboard = [
            [InlineKeyboardButton("🌿 فرع", callback_data="type_branch"),
             InlineKeyboardButton("🍬 حلوة", callback_data="type_sweet")],
            [InlineKeyboardButton("🌾 برغل", callback_data="type_burghul"),
             InlineKeyboardButton("🎭 مارق", callback_data="type_mariq")],
            [InlineKeyboardButton("🎨 شادي الديكور", callback_data="type_shady"),
             InlineKeyboardButton("💃 بنوتي", callback_data="type_banoti")],
            [InlineKeyboardButton("✅ حفظ", callback_data="save_type")],
            [InlineKeyboardButton("🔙 الرجوع", callback_data="go_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🔖 **اختر تصنيفك:** (يمكن اختيار أكثر من واحد)", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in choose_type: {e}")
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# Handle photo
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save user profile picture."""
    try:
        user = update.message.from_user
        file_id = update.message.photo[-1].file_id

        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET photo=? WHERE id=?", (file_id, user.id))
            await db.commit()

        await update.message.reply_text("✅ **تم التسجيل بنجاح! يمكنك الآن البحث عن المستخدمين القريبين.**")
        await start(update, context)
    except Exception as e:
        logger.error(f"Error in handle_photo: {e}")
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# Handle location
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user location updates."""
    try:
        user = update.message.from_user
        location = update.message.location
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET location=? WHERE id=?", (f"{location.latitude},{location.longitude}", user.id))
            await db.commit()
        await update.message.reply_text("📍 **تم تحديث موقعك بنجاح!**")
    except Exception as e:
        logger.error(f"Error in handle_location: {e}")
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# Delete profile
async def delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete user profile."""
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = query.from_user.id
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("DELETE FROM users WHERE id=?", (user_id,))
            await db.commit()
        
        await query.message.reply_text("✅ تم حذف ملفك الشخصي بنجاح.")
        await register(update, context)
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        await query.message.reply_text("❌ فشل في حذف الملف الشخصي. يرجى المحاولة مرة أخرى.")

# Show users functionality
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show users functionality."""
    query = update.callback_query
    await query.answer()

    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT id, name, age, bio FROM users")
            users = await cursor.fetchall()

        if not users:
            await query.message.reply_text("❌ لا يوجد مستخدمين متاحين.")
            return

        keyboard = []
        for user in users:
            user_id, name, age, bio = user
            button_text = f"{name} ({age})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_profile_{user_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("👥 **قائمة المستخدمين:**", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in show_users: {e}")
        await query.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# View profile functionality
async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View profile functionality."""
    query = update.callback_query
    await query.answer()

    try:
        user_id = int(query.data.split("_")[-1])  # Extract user ID from callback data
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT name, age, bio, photo FROM users WHERE id=?", (user_id,))
            user = await cursor.fetchone()

        if not user:
            await query.message.reply_text("❌ المستخدم غير موجود.")
            return

        name, age, bio, photo = user
        profile_text = f"👤 **الاسم:** {name}\n📅 **العمر:** {age}\n📝 **نبذة:** {bio}"
        
        if photo:
            await query.message.reply_photo(photo, caption=profile_text)
        else:
            await query.message.reply_text(profile_text)
    except Exception as e:
        logger.error(f"Error in view_profile: {e}")
        await query.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")

# Go back
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle go back action."""
    query = update.callback_query
    await query.answer()
    await start(update, context)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors."""
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text("❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")

# Main function
async def main():
    """Start bot with updated handlers."""
    try:
        await init_db()  # Initialize database
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.LOCATION, handle_location))
        app.add_handler(CallbackQueryHandler(show_users, pattern="^show_users$"))
        app.add_handler(CallbackQueryHandler(view_profile, pattern="^view_profile_"))
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
