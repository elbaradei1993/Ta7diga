import logging
import asyncio
import nest_asyncio
import aiosqlite
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Configure logging and event loop
nest_asyncio.apply()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"
DATABASE = "users.db"
ADMINS = [1796978458]

# Database initialization
async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            age INTEGER,
            bio TEXT,
            type TEXT,
            photo TEXT
        )""")
        await db.commit()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user.id,))
        if not await cursor.fetchone():
            await register_user(update, context)
            return

    keyboard = [
        [InlineKeyboardButton("🔍 بحث", callback_data="search")],
        [InlineKeyboardButton("👤 ملفي", callback_data="my_profile")],
        [InlineKeyboardButton("🗑️ حذف الحساب", callback_data="delete_account")]
    ]
    await update.message.reply_text("مرحبا! اختر خيارًا:", reply_markup=InlineKeyboardMarkup(keyboard))

# Registration flow
async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✨ مرحبا! سجل نفسك أولا\nأدخل اسمك:")
    context.user_data["registration_stage"] = "name"

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stage = context.user_data.get("registration_stage")
    user = update.message.from_user
    text = update.message.text

    if stage == "name":
        context.user_data["name"] = text
        await update.message.reply_text("كم عمرك؟")
        context.user_data["registration_stage"] = "age"

    elif stage == "age":
        if not text.isdigit():
            await update.message.reply_text("يرجى إدخال عمر صحيح!")
            return
        context.user_data["age"] = int(text)
        await update.message.reply_text("أخبرنا عن نفسك (نبذة قصيرة):")
        context.user_data["registration_stage"] = "bio"

    elif stage == "bio":
        context.user_data["bio"] = text
        keyboard = [[InlineKeyboardButton(t, callback_data=f"type_{t}")] 
                   for t in ["فرع", "حلوة", "برغل"]]
        await update.message.reply_text("اختر تصنيفك:", reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data["registration_stage"] = "type"

# Button handlers
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "delete_account":
        await delete_account(update, context)
    
    elif query.data.startswith("type_"):
        await save_registration(update, context)
    
    elif query.data == "my_profile":
        await show_profile(update, context)
    
    elif query.data == "search":
        await search_users(update, context)

# Save registration data
async def save_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_data = context.user_data
    user_type = query.data.split("_")[1]
    
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""INSERT INTO users 
                          (id, username, name, age, bio, type) 
                          VALUES (?,?,?,?,?,?)""",
                          (query.from_user.id,
                           query.from_user.username,
                           user_data.get("name"),
                           user_data.get("age"),
                           user_data.get("bio"),
                           user_type))
        await db.commit()
    
    await query.message.reply_text("✅ تم التسجيل بنجاح!")
    context.user_data.clear()
    await start(update, context)

# Delete account
async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM users WHERE id=?", (query.from_user.id,))
        await db.commit()
    await query.message.reply_text("🗑️ تم حذف حسابك بنجاح")

# Show user profile
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (query.from_user.id,))
        user = await cursor.fetchone()
    
    if user:
        profile = f"👤 الاسم: {user[2]}\n" \
                  f"📅 العمر: {user[3]}\n" \
                  f"📝 النبذة: {user[4]}\n" \
                  f"🏷 التصنيف: {user[5]}"
        await query.message.reply_text(profile)
    else:
        await query.message.reply_text("❌ لم يتم العثور على الملف الشخصي")

# Search users
async def search_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT id,name FROM users WHERE id != ?", (query.from_user.id,))
        users = await cursor.fetchall()
    
    if not users:
        await query.message.reply_text("🔍 لا يوجد مستخدمين آخرين")
        return
    
    keyboard = [[InlineKeyboardButton(f"{name} ({id})", callback_data=f"view_{id}")] 
               for id, name in users]
    await query.message.reply_text("👥 اختر مستخدمًا:", reply_markup=InlineKeyboardMarkup(keyboard))

# Main application
async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_button))
    
    await app.initialize()
    await app.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
