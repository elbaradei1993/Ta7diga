import logging
import asyncio
import nest_asyncio
import aiosqlite
from geopy.distance import geodesic
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    InputMediaPhoto,
    Bot,
    BotCommandScopeChat
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
import pandas as pd  # For Excel export

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

# List of countries and cities
COUNTRIES = {
    "السودان": [
        "الخرطوم", "أم درمان", "بحري", "بورتسودان", "كسلا", "القضارف", "ود مدني", "الأبيض", "نيالا", "الفاشر",
        "دنقلا", "عطبرة", "كوستي", "سنار", "الضعين", "الدمازين", "شندي", "كريمة", "طوكر", "حلفا الجديدة",
        "وادي حلفا", "أم روابة", "أبو جبيهة", "بابنوسة", "الجنينة", "جزيرة توتي", "الحصاحيصا", "رفاعة", "سنجة",
        "الرنك", "حلفا", "الحديبة", "تندلتي", "الدلنج", "كادوقلي", "بنتيو", "الرهد", "نوري", "أرقين",
        "خشم القربة", "النهود", "مروي", "سواكن", "حلايب", "أبورماد", "عبري", "كتم", "الضعين", "المجلد",
        "كرنوي", "زالنجي"
    ],
    "مصر": ["القاهرة", "الإسكندرية", "الجيزة", "شرم الشيخ"],
    "السعودية": ["الرياض", "جدة", "مكة", "المدينة المنورة"],
    "ليبيا": ["طرابلس", "بنغازي", "مصراتة", "سبها"],
    "الإمارات": ["دبي", "أبوظبي", "الشارقة", "عجمان"]
}

# Registration steps
USERNAME, NAME, AGE, BIO, TYPE, COUNTRY, CITY, LOCATION, PHOTO = range(9)

# Feedback and report steps
FEEDBACK, REPORT = range(2)

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
                    country TEXT,
                    city TEXT,
                    telegram_id INTEGER UNIQUE,
                    banned INTEGER DEFAULT 0,
                    frozen INTEGER DEFAULT 0,
                    admin INTEGER DEFAULT 0
                )"""
            )
            await db.execute(
                """CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            await db.execute(
                """CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            await db.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# Start command (displays welcome message and starts registration)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Start function called.")
    user_id = update.message.from_user.id
    logger.info(f"User {user_id} started registration.")

    # Check if user is already registered
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
            existing_user = await cursor.fetchone()
            if existing_user:
                await update.message.reply_text("✅ أنت مسجل بالفعل. يمكنك استخدام /search للبحث عن مستخدمين قريبين.")
                return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error checking user registration: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التحقق من تسجيلك. الرجاء المحاولة مرة أخرى.")
        return ConversationHandler.END

    # Display the welcome message
    welcome_message = (
        "الأن مع تطبيق تحديقة الجديد تقدر تقابل, تتعرف و تتفاعل مع الناس بي راحتك, حسب الموقع بتاعك 😍\n\n"
        "التطبيق بجيب ليك الناس القريبة منك لغاية 50 كيلو متر...\n"
        "سجل في التطبيق و أبدا مقابلاتك الان...\n\n"
        "التطبيق امن للأستخدام علي عكس التطبيقات الاخري, تقدر تمسحه بضغطة زر واحدة كأنه جزء من محادثاتك العادية "
        "و ما بتحتاج تنزلو في التلفون, التطبيق جاهز علي برنامج تلجرام 😍\n\n"
        "سجل الان!"
    )

    # Create a button to start registration
    keyboard = [[InlineKeyboardButton("بدء التسجيل", callback_data="agree_to_privacy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the welcome message with the button
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    logger.info("Start function completed.")
    return USERNAME

# Handle the user's agreement to the privacy note
async def agree_to_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # Start the registration process
    await query.edit_message_text("📝 بدأت عملية التسجيل!\nالرجاء إرسال اسم المستخدم الخاص بك:")
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

            # Store username in context
            context.user_data['username'] = username
            await update.message.reply_text("💬 الآن أرسل اسمك الكامل:")
            return NAME
    except Exception as e:
        logger.error(f"Error checking username: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التحقق من اسم المستخدم. الرجاء المحاولة مرة أخرى.")
        return USERNAME

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

    # Create buttons for countries
    keyboard = [[InlineKeyboardButton(country, callback_data=f"country_{country}")] for country in COUNTRIES.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("🌍 اختر بلدك:", reply_markup=reply_markup)
    return COUNTRY

# Set country
async def set_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    country = query.data.split('_')[1]  # Extract country name from callback data
    context.user_data['country'] = country

    # Create buttons for cities in the selected country
    keyboard = [[InlineKeyboardButton(city, callback_data=f"city_{city}")] for city in COUNTRIES[country]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"✅ تم اختيار البلد: {country}")
    await query.message.reply_text("🏙️ اختر مدينتك:", reply_markup=reply_markup)
    return CITY

# Set city
async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    city = query.data.split('_')[1]  # Extract city name from callback data
    context.user_data['city'] = city
    await query.edit_message_text(f"✅ تم اختيار المدينة: {city}")
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
                "INSERT INTO users (id, username, name, age, bio, type, location, photo, country, city, telegram_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (update.message.from_user.id,
                 context.user_data['username'],
                 context.user_data['name'],
                 context.user_data['age'],
                 context.user_data['bio'],
                 context.user_data['type'],
                 context.user_data['location'],
                 context.user_data['photo'],
                 context.user_data['country'],
                 context.user_data['city'],
                 update.message.from_user.id)
            )
            await db.commit()

        await update.message.reply_text("✅ تم التسجيل بنجاح!")

        # Notify admin about the new user
        await notify_admin(update, context)

        # Automatically show nearby profiles after registration
        await show_nearby_profiles(update, context)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in set_photo: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التسجيل. الرجاء المحاولة مرة أخرى.")
        return ConversationHandler.END

# Notify admin about new user registration
async def notify_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_data = context.user_data
        message = (
            "👤 مستخدم جديد مسجل:\n\n"
            f"الاسم: {user_data['name']}\n"
            f"العمر: {user_data['age']}\n"
            f"النوع: {user_data['type']}\n"
            f"البلد: {user_data['country']}\n"
            f"المدينة: {user_data['city']}\n"
            f"الموقع: {user_data['location']}\n"
            f"معرف التليجرام: {update.message.from_user.id}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception as e:
        logger.error(f"Error notifying admin: {e}")

# Show nearby profiles
async def show_nearby_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Get user's location from database
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT location FROM users WHERE telegram_id = ?", (update.message.from_user.id,))
            user_location = await cursor.fetchone()
            if not user_location or not user_location[0]:
                await update.message.reply_text("❗ الرجاء التسجيل أولاً باستخدام /start لتحديد موقعك.")
                return

            user_coords = tuple(map(float, user_location[0].split(',')))
            async with db.execute("SELECT * FROM users WHERE id != ? AND banned = 0", (update.message.from_user.id,)) as cursor:
                profiles = []
                async for row in cursor:
                    if not row[6]:  # Skip if no location
                        continue
                    profile_coords = tuple(map(float, row[6].split(',')))
                    distance = geodesic(user_coords, profile_coords).km
                    profiles.append({
                        "id": row[0],
                        "name": row[2],
                        "age": row[3],
                        "type": row[5],
                        "city": row[9],
                        "country": row[8],
                        "photo": row[7],
                        "telegram_id": row[10],
                        "distance": distance
                    })

                if not profiles:
                    await update.message.reply_text("😔 لا يوجد مستخدمون مسجلون.")
                    return

                # Sort profiles by distance (nearest first)
                profiles.sort(key=lambda x: x['distance'])

                # Show profiles within 50 km
                for profile in profiles:
                    if profile['distance'] <= 50:
                        profile_card = (
                            f"👤 الاسم: {profile['name']}\n"
                            f"📅 العمر: {profile['age']}\n"
                            f"🔄 النوع: {profile['type']}\n"
                            f"📍 المدينة: {profile['city']}, {profile['country']}\n"
                            f"📏 المسافة: {round(profile['distance'], 1)} كم"
                        )

                        keyboard = [
                            [InlineKeyboardButton("📩 إرسال رسالة", url=f"tg://user?id={profile['telegram_id']}")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        await update.message.reply_photo(
                            photo=profile['photo'],
                            caption=profile_card,
                            reply_markup=reply_markup
                        )
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
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                count = await cursor.fetchone()
                if count[0] == 0:
                    await update.message.reply_text("😔 لا يوجد مستخدمون مسجلون.")
                    return

            async with db.execute("SELECT * FROM users") as cursor:
                keyboard = []
                async for row in cursor:
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

# Export user data to Excel
async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Fetch all user data
            cursor = await db.execute("SELECT * FROM users")
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            # Convert to a pandas DataFrame
            df = pd.DataFrame(rows, columns=columns)

            # Save the DataFrame to an Excel file
            excel_file = "users_data.xlsx"
            df.to_excel(excel_file, index=False)

            # Send the Excel file to the admin
            with open(excel_file, "rb") as file:
                await update.message.reply_document(document=file, caption="📊 بيانات المستخدمين")

            # Delete the Excel file after sending
            os.remove(excel_file)

            logger.info(f"User data exported by admin {user_id}.")
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تصدير بيانات المستخدمين. الرجاء المحاولة مرة أخرى.")

# Broadcast command
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    await update.message.reply_text("📢 الرجاء إرسال الرسالة التي تريد بثها:")
    context.user_data['awaiting_broadcast'] = True

# Handle broadcast
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('awaiting_broadcast'):
        broadcast_text = update.message.text.strip()
        if not broadcast_text:
            await update.message.reply_text("❌ الرجاء إدخال رسالة صحيحة.")
            return

        try:
            async with aiosqlite.connect(DATABASE) as db:
                async with db.execute("SELECT telegram_id FROM users") as cursor:
                    users = await cursor.fetchall()
                    for user in users:
                        try:
                            await context.bot.send_message(chat_id=user[0], text=broadcast_text)
                        except Exception as e:
                            logger.error(f"Error sending broadcast to user {user[0]}: {e}")
            await update.message.reply_text("✅ تم بث الرسالة بنجاح!")
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            await update.message.reply_text("❌ حدث خطأ أثناء البث. الرجاء المحاولة مرة أخرى.")
        context.user_data['awaiting_broadcast'] = False

# Feedback command
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📝 الرجاء إرسال تعليقك:")
    return FEEDBACK

# Handle feedback
async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    feedback_text = update.message.text.strip()
    if not feedback_text:
        await update.message.reply_text("❌ الرجاء إدخال تعليق صحيح.")
        return FEEDBACK

    try:
        # Store feedback in database
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT INTO feedback (user_id, message) VALUES (?, ?)",
                (update.message.from_user.id, feedback_text)
            )
            await db.commit()

        # Send feedback to admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📝 تعليق جديد من المستخدم {update.message.from_user.id}:\n{feedback_text}"
        )
        
        await update.message.reply_text("✅ تم استلام تعليقك. شكراً لك!")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error handling feedback: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إرسال التعليق. الرجاء المحاولة مرة أخرى.")
        return FEEDBACK

# Report user command
async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚨 الرجاء إرسال تقريرك:")
    return REPORT

# Handle report
async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    report_text = update.message.text.strip()
    if not report_text:
        await update.message.reply_text("❌ الرجاء إدخال تقرير صحيح.")
        return REPORT

    try:
        # Store report in database
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT INTO reports (user_id, message) VALUES (?, ?)",
                (update.message.from_user.id, report_text)
            )
            await db.commit()

        # Send report to admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚨 تقرير جديد من المستخدم {update.message.from_user.id}:\n{report_text}"
        )
        
        await update.message.reply_text("✅ تم استلام تقريرك. شكراً لك!")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error handling report: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إرسال التقرير. الرجاء المحاولة مرة أخرى.")
        return REPORT

# Admin reply to feedback/report
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    try:
        # Extract user ID and message from the command
        args = update.message.text.split(maxsplit=2)
        if len(args) < 3:
            await update.message.reply_text("❌ الرجاء استخدام الصيغة الصحيحة: /reply <user_id> <message>")
            return

        target_user_id = int(args[1])
        message = args[2]

        # Send the message to the target user
        await context.bot.send_message(chat_id=target_user_id, text=f"📨 رد من الإدارة:\n{message}")
        await update.message.reply_text(f"✅ تم إرسال الرد إلى المستخدم {target_user_id}.")
    except Exception as e:
        logger.error(f"Error in admin_reply: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إرسال الرد. الرجاء المحاولة مرة أخرى.")

# Main menu button
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Display the main menu
    await start(update, context)

# Set bot commands
async def set_bot_commands(application):
    # Set commands for all users
    commands = [
        ("start", "بدء التسجيل"),
        ("search", "البحث عن مستخدمين قريبين"),
        ("feedback", "إرسال تعليق"),
        ("report", "الإبلاغ عن مستخدم"),
    ]
    await application.bot.set_my_commands(commands)

    # Set additional commands for admin
    admin_commands = [
        ("admin", "لوحة التحكم (للمشرفين فقط)"),
        ("export", "تصدير بيانات المستخدمين (للمشرفين فقط)"),
        ("broadcast", "بث رسالة لجميع المستخدمين (للمشرفين فقط)"),
        ("reply", "الرد على مستخدم (للمشرفين فقط)"),
    ]
    await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(ADMIN_ID))

# Main function
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).get_updates_pool_timeout(30).build()

    # Conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [
                CallbackQueryHandler(agree_to_privacy, pattern="^agree_to_privacy$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_username)
            ],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_age)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_bio)],
            TYPE: [CallbackQueryHandler(set_type)],
            COUNTRY: [CallbackQueryHandler(set_country)],
            CITY: [CallbackQueryHandler(set_city)],
            LOCATION: [MessageHandler(filters.LOCATION, set_location)],
            PHOTO: [MessageHandler(filters.PHOTO, set_photo)],
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )

    # Conversation handler for feedback
    feedback_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', feedback)],
        states={
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )

    # Conversation handler for reporting
    report_handler = ConversationHandler(
        entry_points=[CommandHandler('report', report_user)],
        states={
            REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report)],
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(feedback_handler)
    application.add_handler(report_handler)
    application.add_handler(CommandHandler('search', show_nearby_profiles))
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CommandHandler('export', export_users))
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(CommandHandler('reply', admin_reply))
    application.add_handler(CallbackQueryHandler(admin_profile_actions, pattern="^admin_profile_"))
    application.add_handler(CallbackQueryHandler(ban_user, pattern="^ban_"))
    application.add_handler(CallbackQueryHandler(freeze_user, pattern="^freeze_"))
    application.add_handler(CallbackQueryHandler(promote_user, pattern="^promote_"))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))

    # Set bot commands
    await set_bot_commands(application)

    # Run the bot
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(init_db())  # Initialize the database
    asyncio.run(main())
