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
    filters,
    ConversationHandler
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

# Registration steps
USERNAME, NAME, AGE, BIO, TYPE, LOCATION, PHOTO = range(7)

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
                photo TEXT
            )"""
        )
        await db.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "مرحبًا بك! 🏳️‍🌈\n"
        "قم بإنشاء ملفك الشخصي باستخدام الأمر /register.\n"
        "يمكنك البحث عن مستخدمين قريبين منك باستخدام الأمر /search.\n"
        "لعرض ملفك الشخصي استخدم الأمر /profile."
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Starting registration process")
    await update.message.reply_text("📝 ابدأ التسجيل!\nالرجاء إرسال اسم المستخدم الخاص بك:")
    return USERNAME

async def set_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text("💬 الآن أرسل اسمك الكامل:")
    return NAME

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text("📅 الآن أرسل عمرك:")
    return AGE

async def set_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['age'] = update.message.text
    await update.message.reply_text("🖋️ الآن أرسل سيرتك الذاتية:")
    return BIO

async def set_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['bio'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("سالب", callback_data="سالب")],
        [InlineKeyboardButton("موجب", callback_data="موجب")],
        [InlineKeyboardButton("مبادل", callback_data="مبادل")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔄 اختر نوعك:", reply_markup=reply_markup)
    return TYPE

async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    await query.edit_message_text(f"✅ تم اختيار النوع: {query.data}")
    await query.message.reply_text("📍 الآن أرسل موقعك الجغرافي من خلال مشاركة موقعك مباشرة عبر هاتفك:")
    return LOCATION

async def set_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        context.user_data['location'] = f"{lat},{lon}"
        await update.message.reply_text("📷 الآن أرسل صورتك الشخصية:")
        return PHOTO
    else:
        await update.message.reply_text("❌ الرجاء مشاركة موقعك الجغرافي باستخدام زر الموقع في هاتفك.")
        return LOCATION

async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = update.message.photo[-1].file_id
    context.user_data['photo'] = photo_file

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (id, username, name, age, bio, type, location, photo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (update.message.from_user.id,
             context.user_data['username'],
             context.user_data['name'],
             context.user_data['age'],
             context.user_data['bio'],
             context.user_data['type'],
             context.user_data['location'],
             context.user_data['photo'])
        )
        await db.commit()

    await update.message.reply_text("✅ تم تسجيلك بنجاح!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ تم إلغاء التسجيل.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")

async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    register_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_username)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_age)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_bio)],
            TYPE: [CallbackQueryHandler(set_type)],
            LOCATION: [MessageHandler(filters.LOCATION, set_location)],
            PHOTO: [MessageHandler(filters.PHOTO, set_photo)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(register_handler)
    app.add_error_handler(error_handler)

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
