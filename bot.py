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
ADMIN_ID = 1796978458  # Admin user ID
WEB_APP_URL = "https://t.me/Ta7digaBot/Ta7diga"  # Replace with your web app URL

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
                    photo TEXT,
                    banned INTEGER DEFAULT 0,
                    frozen INTEGER DEFAULT 0,
                    admin INTEGER DEFAULT 0
                )"""
            )
            await db.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# Start command (starts registration directly)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    logger.info(f"User {user_id} started registration.")

    # Check if the user is already registered
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            existing_user = await cursor.fetchone()
            if existing_user:
                await update.message.reply_text("✅ أنت مسجل بالفعل! استخدم /search للبحث عن مستخدمين قريبين.")
                return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error checking user registration: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التحقق من التسجيل. الرجاء المحاولة مرة أخرى.")
        return ConversationHandler.END

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
        await update.message.reply_text("❗ الرجاء التسجيل أولاً باستخدام /start لتحديد موقعك.")
        return

    user_coords = tuple(map(float, user_location.split(',')))
    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT * FROM users WHERE id != ? AND banned = 0", (update.message.from_user.id,)) as cursor:
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

# Admin panel command
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى لوحة التحكم.")
        return

    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT * FROM users") as cursor:
                keyboard = []
                async for row in cursor:
                    # Create a profile card for each user
                    profile_text = (
                        f"👤 الاسم: {row[2]}\n"
                        f"📅 العمر: {row[3]}\n"
                        f"🖋️ النبذة: {row[4]}\n"
                        f"🔄 النوع: {row[5]}\n"
                        f"📍 الموقع: [فتح في خرائط جوجل](https://www.google.com/maps?q={row[6]})\n"
                        f"📸 الصورة: [عرض الصورة]({row[7]})"
                    )
                    keyboard.append([InlineKeyboardButton(f"👤 {row[2]}", callback_data=f"admin_profile_{row[0]}")])

                if keyboard:
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text("👤 المستخدمون المسجلون:", reply_markup=reply_markup)
                else:
                    await update.message.reply_text("😔 لا يوجد مستخدمون مسجلون.")
    except Exception as e:
        logger.error(f"Error in admin_panel: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تحميل لوحة التحكم. الرجاء المحاولة مرة أخرى.")

# Admin profile actions
async def admin_profile_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[2])  # Extract user ID from callback data
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()

            if user:
                # Create a profile card
                profile_text = (
                    f"👤 الاسم: {user[2]}\n"
                    f"📅 العمر: {user[3]}\n"
                    f"🖋️ النبذة: {user[4]}\n"
                    f"🔄 النوع: {user[5]}\n"
                    f"📍 الموقع: [فتح في خرائط جوجل](https://www.google.com/maps?q={user[6]})\n"
                    f"📸 الصورة: [عرض الصورة]({user[7]})"
                )

                # Create action buttons
                keyboard = [
                    [InlineKeyboardButton("❌ حظر", callback_data=f"ban_{user[0]}")],
                    [InlineKeyboardButton("❄️ تجميد", callback_data=f"freeze_{user[0]}")],
                    [InlineKeyboardButton("⭐ ترقية", callback_data=f"promote_{user[0]}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Send the profile card with action buttons
                await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_profile_actions: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء تحميل الملف الشخصي. الرجاء المحاولة مرة أخرى.")

# Ban user callback
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[1])  # Extract user ID from callback data
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET banned = 1 WHERE id = ?", (user_id,))
            await db.commit()
        await query.edit_message_text(f"✅ تم حظر المستخدم بنجاح.")
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء حظر المستخدم. الرجاء المحاولة مرة أخرى.")

# Freeze user callback
async def freeze_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[1])  # Extract user ID from callback data
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET frozen = 1 WHERE id = ?", (user_id,))
            await db.commit()
        await query.edit_message_text(f"✅ تم تجميد المستخدم بنجاح.")
    except Exception as e:
        logger.error(f"Error freezing user: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء تجميد المستخدم. الرجاء المحاولة مرة أخرى.")

# Promote user callback
async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[1])  # Extract user ID from callback data
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET admin = 1 WHERE id = ?", (user_id,))
            await db.commit()
        await query.edit_message_text(f"✅ تم ترقية المستخدم إلى مشرف بنجاح.")
    except Exception as e:
        logger.error(f"Error promoting user: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء ترقية المستخدم. الرجاء المحاولة مرة أخرى.")

# Launch mini Telegram app
async def launch_mini_app(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("فتح التطبيق المصغر", web_app={"url": WEB_APP_URL})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🚀 اضغط على الزر أدناه لفتح التطبيق المصغر:", reply_markup=reply_markup)

# Function to set bot commands
async def set_bot_commands(application):
    commands = [
        ("start", "بدء التسجيل"),
        ("search", "البحث عن مستخدمين قريبين"),
        ("admin", "لوحة التحكم (للمشرفين فقط)"),
        ("app", "فتح التطبيق المصغر"),
    ]
    await application.bot.set_my_commands(commands)

# Main function
def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Set bot commands
    application.post_init = set_bot_commands

    # Conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
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
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('search', show_nearby_profiles))
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CommandHandler('app', launch_mini_app))
    application.add_handler(CallbackQueryHandler(admin_profile_actions, pattern="^admin_profile_"))
    application.add_handler(CallbackQueryHandler(ban_user, pattern="^ban_"))
    application.add_handler(CallbackQueryHandler(freeze_user, pattern="^freeze_"))
    application.add_handler(CallbackQueryHandler(promote_user, pattern="^promote_"))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    asyncio.run(init_db())  # Initialize the database
    main()
