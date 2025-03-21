import logging
import asyncio
import nest_asyncio
import aiosqlite
from geopy.distance import geodesic
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
import telegram.error

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
    await update.message.reply_text(
        "مرحبًا بك! 🏳️‍🌈\n"
        "قم بإنشاء ملفك الشخصي باستخدام الأمر /profile.\n"
        "يمكنك البحث عن مستخدمين قريبين منك باستخدام الأمر /search."
    )

async def ask_for_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("سالب", callback_data="type_salb")],
        [InlineKeyboardButton("موجب", callback_data="type_mojab")],
        [InlineKeyboardButton("مبادل", callback_data="type_mubadel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔹 اختر نوعك:", reply_markup=reply_markup)

async def type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    selected_type = query.data.split("_")[1]  # Extract 'salb', 'mojab', or 'mubadel'

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE users SET type = ? WHERE id = ?", (selected_type, query.from_user.id))
        await db.commit()

    await query.answer("✅ تم تحديث نوعك بنجاح.")
    await query.message.edit_text(f"🌐 نوعك الحالي: {selected_type}")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT location FROM users WHERE id=?", (user_id,))
        user_location = await cursor.fetchone()

        if not user_location or not user_location[0]:
            await update.message.reply_text("❌ لم يتم تعيين موقعك. يرجى تحديث موقعك أولًا.")
            return

        user_coords = tuple(map(float, user_location[0].split(',')))
        cursor = await db.execute("SELECT id, name, location, photo FROM users WHERE id != ?", (user_id,))
        results = await cursor.fetchall()

    nearby_profiles = []
    for profile in results:
        if profile[2]:
            profile_coords = tuple(map(float, profile[2].split(',')))
            distance = geodesic(user_coords, profile_coords).km
            if distance <= 10:  # 10 km radius
                nearby_profiles.append(profile)

    if not nearby_profiles:
        await update.message.reply_text("🔍 لا توجد ملفات شخصية قريبة منك.")
        return

    keyboard = [
        [InlineKeyboardButton(profile[1], callback_data=f"view_profile_{profile[0]}")]
        for profile in nearby_profiles
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📍 المستخدمون القريبون منك:", reply_markup=reply_markup)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")

async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", ask_for_type))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(type_selection, pattern="^type_"))
    app.add_error_handler(error_handler)

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
