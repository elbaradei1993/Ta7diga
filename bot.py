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
import os

# Apply nest_asyncio for Jupyter/Notebook environments
nest_asyncio.apply()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration (use environment variables for sensitive data)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak")  # Replace with your bot token
DATABASE = os.getenv("DATABASE", "users.db")  # Database file
ADMINS = [1796978458]  # List of admin user IDs

# Registration steps
USERNAME, NAME, AGE, BIO, TYPE, LOCATION, PHOTO = range(7)

# Initialize the database
async def init_db():
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    name TEXT,
                    age INTEGER,
                    bio TEXT,
                    type TEXT,
                    location TEXT,
                    photo TEXT
                )"""
            )
            await db.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "أهلاً بك! 🌍\n"
        "قم بإنشاء ملفك الشخصي باستخدام /register.\n"
        "للبحث عن المستخدمين القريبين استخدم /search.\n"
        "لعرض ملفك الشخصي استخدم /profile."
    )

# Register command
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"User {update.message.from_user.id} started registration.")
    await update.message.reply_text("📝 بدأت عملية التسجيل!\nالرجاء إرسال اسم المستخدم الخاص بك:")
    return USERNAME

# Set username
async def set_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip()
    if not username:
        await update.message.reply_text("❌ الرجاء إدخال اسم مستخدم صحيح.")
        return USERNAME

    # Check if username already exists
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
            existing_user = await cursor.fetchone()
            if existing_user:
                await update.message.reply_text("❌ اسم المستخدم موجود بالفعل. الرجاء اختيار اسم آخر.")
                return USERNAME
    except Exception as e:
        logger.error(f"Error checking username: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التحقق من اسم المستخدم. الرجاء المحاولة مرة أخرى.")
        return USERNAME

    context.user_data['username'] = username
    await update.message.reply_text("💬 الآن أرسل اسمك الكامل:")
    return NAME

# Set name
async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ الرجاء إدخال اسم صحيح.")
        return NAME

    context.user_data['name'] = name
    await update.message.reply_text("📅 الآن أرسل عمرك:")
    return AGE

# Set age
async def set_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text.strip())
        if age < 18 or age > 100:
            await update.message.reply_text("❌ الرجاء إدخال عمر صحيح بين 18 و 100.")
            return AGE
        context.user_data['age'] = age
        await update.message.reply_text("🖋️ الآن أرسل نبذة قصيرة عنك:")
        return BIO
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال عمر صحيح.")
        return AGE

# Set bio
async def set_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    bio = update.message.text.strip()
    if not bio:
        await update.message.reply_text("❌ الرجاء إدخال نبذة صحيحة.")
        return BIO

    context.user_data['bio'] = bio
    keyboard = [
        [InlineKeyboardButton("سالب", callback_data="سالب")],
        [InlineKeyboardButton("موجب", callback_data="موجب")],
        [InlineKeyboardButton("مبادل", callback_data="مبادل")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔄 اختر النوع الخاص بك:", reply_markup=reply_markup)
    return TYPE

# Set type
async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    await query.edit_message_text(f"✅ تم اختيار النوع: {query.data}")
    await query.message.reply_text("📍 الآن أرسل موقعك بمشاركته مباشرة من هاتفك:")
    return LOCATION

# Set location
async def set_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            context.user_data['location'] = f"{lat},{lon}"
            await update.message.reply_text("📷 الآن أرسل صورتك الشخصية:")
            return PHOTO
        else:
            await update.message.reply_text("❌ الرجاء مشاركة موقع صحيح.")
            return LOCATION
    else:
        await update.message.reply_text("❌ الرجاء مشاركة موقعك باستخدام زر الموقع في هاتفك.")
        return LOCATION

# Set photo
async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        if not update.message.photo:
            await update.message.reply_text("❌ الرجاء إرسال صورة صحيحة.")
            return PHOTO

        photo_file = update.message.photo[-1].file_id
        context.user_data['photo'] = photo_file

        # Save user data to the database
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

        # Automatically show nearby profiles after registration
        await show_nearby_profiles(update, context)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in set_photo: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التسجيل. الرجاء المحاولة مرة أخرى.")
        return ConversationHandler.END

# Show nearby profiles
async def show_nearby_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_location = context.user_data.get('location')
    if not user_location:
        await update.message.reply_text("❗ الرجاء التسجيل أولاً باستخدام /register لتحديد موقعك.")
        return

    user_coords = tuple(map(float, user_location.split(',')))
    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT * FROM users WHERE id != ?", (update.message.from_user.id,)) as cursor:
                profiles = []
                async for row in cursor:
                    profile_coords = tuple(map(float, row[6].split(',')))
                    distance = geodesic(user_coords, profile_coords).km
                    profiles.append({
                        "id": row[0],
                        "name": row[2],
                        "age": row[3],
                        "type": row[5],
                        "distance": distance
                    })

                # Sort profiles by distance (nearest to farthest)
                profiles.sort(key=lambda x: x['distance'])

                # Create buttons for nearby profiles
                keyboard = []
                for profile in profiles:
                    if profile['distance'] <= 50:  # Only show profiles within 50 km
                        button_text = f"{profile['name']}, {profile['age']} سنة - {profile['type']} ({round(profile['distance'], 1)} كم)"
                        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"profile_{profile['id']}")])

                if keyboard:
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text("🔍 المستخدمون القريبون منك:", reply_markup=reply_markup)
                else:
                    await update.message.reply_text("😔 لم يتم العثور على ملفات قريبة.")
    except Exception as e:
        logger.error(f"Error in show_nearby_profiles: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء البحث. الرجاء المحاولة مرة أخرى.")

# Main function
def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_username)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_age)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_bio)],
            TYPE: [CallbackQueryHandler(set_type)],
            LOCATION: [MessageHandler(filters.LOCATION, set_location)],
            PHOTO: [MessageHandler(filters.PHOTO, set_photo)],
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('search', show_nearby_profiles))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    asyncio.run(init_db())  # Initialize the database
    main()
