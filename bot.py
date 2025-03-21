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
        await ask_registration_details(update, context)
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

async def ask_registration_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👤 ما اسمك؟")
    context.user_data['register_step'] = 'name'

async def registration_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    text = update.message.text
    step = context.user_data.get('register_step')

    if step == 'name':
        context.user_data['name'] = text
        await update.message.reply_text("📅 كم عمرك؟")
        context.user_data['register_step'] = 'age'
    elif step == 'age':
        context.user_data['age'] = text
        await update.message.reply_text("💬 اكتب نبذة قصيرة عنك.")
        context.user_data['register_step'] = 'bio'
    elif step == 'bio':
        context.user_data['bio'] = text
        keyboard = [
            [InlineKeyboardButton("سالب", callback_data="type_bottom")],
            [InlineKeyboardButton("موجب", callback_data="type_top")],
            [InlineKeyboardButton("مبادل", callback_data="type_switch")]
        ]
        await update.message.reply_text("🌐 اختر نوعك:", reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data['register_step'] = 'type'
    elif step == 'photo':
        context.user_data['photo'] = text
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("""
                INSERT INTO users (id, username, name, age, bio, type, location, photo, tribes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user.id, user.username, context.user_data['name'],
                   context.user_data['age'], context.user_data['bio'],
                   context.user_data['type'], None, context.user_data['photo'], None))
            await db.commit()

        await update.message.reply_text("✅ تم إنشاء ملفك الشخصي بنجاح!")

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
                        f"🌐 النوع: {profile_data[5]}\n"
                        f"📍 الموقع: {profile_data[6]}\n")
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registration_handler))

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
