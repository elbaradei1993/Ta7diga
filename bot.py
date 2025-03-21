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

nest_asyncio.apply()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"
DATABASE = "users.db"
ADMINS = [1796978458]

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user.id,))
        result = await cursor.fetchone()

    if not result:
        await update.message.reply_text("🔹 **يرجى التسجيل أولًا.**")
        await register_user(update, context)
        return

    keyboard = [
        [InlineKeyboardButton("🔍 البحث", callback_data="search")],
        [InlineKeyboardButton("👥 عرض المستخدمين", callback_data="show_users")],
        [InlineKeyboardButton("📝 تعديل الملف", callback_data="edit_profile")],
        [InlineKeyboardButton("📍 تحديث موقعي", callback_data="update_location")],
        [InlineKeyboardButton("🗑️ حذف الملف", callback_data="delete_profile")],
        [InlineKeyboardButton("⚙ الإعدادات", callback_data="settings")],
    ]

    if user.id in ADMINS:
        keyboard.append([InlineKeyboardButton("🔧 لوحة الإدارة", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌟 **مرحبًا بك في تحديقة!** اختر من القائمة:", reply_markup=reply_markup)

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📸 يرجى إرسال صورتك الشخصية أو الضغط على زر التخطي.", 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("تخطي", callback_data="skip_photo")]]))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        profile_data = await cursor.fetchone()

    if profile_data:
        profile_text = (f"📋 **ملفك الشخصي**\n"
                        f"👤 الاسم: {profile_data[2]}\n"
                        f"📅 العمر: {profile_data[3]}\n"
                        f"💬 نبذة: {profile_data[4]}\n"
                        f"📍 الموقع: {profile_data[6]}\n"
                        f"🌐 النوع: {profile_data[5]}\n")
        await update.message.reply_text(profile_text)
    else:
        await update.message.reply_text("❌ لم يتم العثور على ملفك الشخصي.")

async def delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM users WHERE id=?", (user_id,))
        await db.commit()

    await query.message.reply_text("✅ تم حذف ملفك الشخصي بنجاح.")

async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CallbackQueryHandler(delete_profile, pattern="^delete_profile$"))
    app.add_handler(CallbackQueryHandler(register_user, pattern="^skip_photo$"))

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
