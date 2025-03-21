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
        "أهلاً بك! 🌍\n"
        "قم بإنشاء ملفك الشخصي باستخدام /register.\n"
        "للبحث عن المستخدمين القريبين استخدم /search.\n"
        "لعرض ملفك الشخصي استخدم /profile."
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("بدء عملية التسجيل")
    await update.message.reply_text("📝 بدأت عملية التسجيل!\nالرجاء إرسال اسم المستخدم الخاص بك:")
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
    await update.message.reply_text("🖋️ الآن أرسل نبذة قصيرة عنك:")
    return BIO

async def set_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['bio'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("سالب", callback_data="سالب")],
        [InlineKeyboardButton("موجب", callback_data="موجب")],
        [InlineKeyboardButton("مبادل", callback_data="مبادل")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔄 اختر النوع الخاص بك:", reply_markup=reply_markup)
    return TYPE

async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    await query.edit_message_text(f"✅ تم اختيار النوع: {query.data}")
    await query.message.reply_text("📍 الآن أرسل موقعك بمشاركته مباشرة من هاتفك:")
    return LOCATION

async def set_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        context.user_data['location'] = f"{lat},{lon}"
        await update.message.reply_text("📷 الآن أرسل صورتك الشخصية:")
        return PHOTO
    else:
        await update.message.reply_text("❌ الرجاء مشاركة موقعك باستخدام زر الموقع في هاتفك.")
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

    await update.message.reply_text("✅ تم التسجيل بنجاح!")
    return ConversationHandler.END

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_location = context.user_data.get('location')
    if not user_location:
        await update.message.reply_text("❗ الرجاء التسجيل أولاً باستخدام /register.")
        return

    user_coords = tuple(map(float, user_location.split(',')))
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT * FROM users") as cursor:
            keyboard = []
            async for row in cursor:
                profile_coords = tuple(map(float, row[6].split(',')))
                distance = geodesic(user_coords, profile_coords).km
                if distance <= 50:
                    keyboard.append([
                        InlineKeyboardButton(f"{row[2]}, {row[3]} سنة - {row[5]}",
                                             callback_data=f"profile_{row[0]}")
                    ])

            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("🔍 المستخدمون القريبون:", reply_markup=reply_markup)
            else:
                await update.message.reply_text("😔 لم يتم العثور على ملفات قريبة.")
