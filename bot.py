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
    BotCommandScopeChat,
    ChatMember
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
import pandas as pd
from datetime import datetime

# Apply nest_asyncio for Jupyter/Notebook environments
nest_asyncio.apply()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak")
DATABASE = os.getenv("DATABASE", "users.db")
ADMIN_ID = 1796978458

# List of countries and cities
COUNTRIES = {
    "السودان": [
        "الخرطوم", "أم درمان", "بحري", "بورتسودان", "كسلا", "القضارف", "ود مدني", 
        "الأبيض", "نيالا", "الفاشر", "دنقلا", "عطبرة", "كوستي", "سنار", "الضعين",
        "الدمازين", "شندي", "كريمة", "طوكر", "حلفا الجديدة", "وادي حلفا", "أم روابة",
        "أبو جبيهة", "بابنوسة", "الجنينة", "جزيرة توتي", "الحصاحيصا", "رفاعة", "سنجة",
        "الرنك", "حلفا", "الحديبة", "تندلتي", "الدلنج", "كادوقلي", "بنتيو", "الرهد",
        "نوري", "أرقين", "خشم القربة", "النهود", "مروي", "سواكن", "حلايب", "أبورماد",
        "عبري", "كتم", "الضعين", "المجلد", "كرنوي", "زالنجي"
    ],
    "مصر": ["القاهرة", "الإسكندرية", "الجيزة", "شرم الشيخ"],
    "السعودية": ["الرياض", "جدة", "مكة", "المدينة المنورة"],
    "ليبيا": ["طرابلس", "بنغازي", "مصراتة", "سبها"],
    "الإمارات": ["دبي", "أبوظبي", "الشارقة", "عجمان"]
}

# Conversation states
USERNAME, NAME, AGE, BIO, TYPE, COUNTRY, CITY, LOCATION, PHOTO = range(9)
FEEDBACK, REPORT = range(2)

async def init_db():
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
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
                    admin INTEGER DEFAULT 0,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            
            # Group members table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    user_id INTEGER,
                    group_id INTEGER,
                    group_title TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, group_id)
                )""")
            
            # Feedback and reports tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            
            await db.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

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

async def agree_to_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 بدأت عملية التسجيل!\nالرجاء إرسال اسم المستخدم الخاص بك:")
    return USERNAME

async def set_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip()
    if not username:
        await update.message.reply_text("❌ الرجاء إدخال اسم مستخدم صحيح.")
        return USERNAME

    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
            existing_user = await cursor.fetchone()
            if existing_user:
                await update.message.reply_text("❌ اسم المستخدم موجود بالفعل. الرجاء اختيار اسم آخر.")
                return USERNAME

            context.user_data['username'] = username
            await update.message.reply_text("💬 الآن أرسل اسمك الكامل:")
            return NAME
    except Exception as e:
        logger.error(f"Error checking username: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التحقق من اسم المستخدم. الرجاء المحاولة مرة أخرى.")
        return USERNAME

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ الرجاء إدخال اسم صحيح.")
        return NAME

    context.user_data['name'] = name
    await update.message.reply_text("📅 الآن أرسل عمرك:")
    return AGE

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

async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    await query.edit_message_text(f"✅ تم اختيار النوع: {query.data}")

    keyboard = [[InlineKeyboardButton(country, callback_data=f"country_{country}")] for country in COUNTRIES.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("🌍 اختر بلدك:", reply_markup=reply_markup)
    return COUNTRY

async def set_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    country = query.data.split('_')[1]
    context.user_data['country'] = country

    keyboard = [[InlineKeyboardButton(city, callback_data=f"city_{city}")] for city in COUNTRIES[country]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"✅ تم اختيار البلد: {country}")
    await query.message.reply_text("🏙️ اختر مدينتك:", reply_markup=reply_markup)
    return CITY

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    city = query.data.split('_')[1]
    context.user_data['city'] = city
    await query.edit_message_text(f"✅ تم اختيار المدينة: {city}")
    await query.message.reply_text("📍 الآن أرسل موقعك بمشاركته مباشرة من هاتفك:")
    return LOCATION

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

async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        if not update.message.photo:
            await update.message.reply_text("❌ الرجاء إرسال صورة صحيحة.")
            return PHOTO

        photo_file = update.message.photo[-1].file_id
        context.user_data['photo'] = photo_file

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
        await notify_admin(update, context)
        await show_nearby_profiles(update, context)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in set_photo: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التسجيل. الرجاء المحاولة مرة أخرى.")
        return ConversationHandler.END

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

async def show_nearby_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
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

                profiles.sort(key=lambda x: x['distance'])

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

async def admin_profile_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[2])
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()

            if user:
                profile_text = (
                    f"👤 الاسم: {user[2]}\n"
                    f"📅 العمر: {user[3]}\n"
                    f"🖋️ النبذة: {user[4]}\n"
                    f"🔄 النوع: {user[5]}\n"
                    f"📍 الموقع: [فتح في خرائط جوجل](https://www.google.com/maps?q={user[6]})\n"
                    f"📸 الصورة: [عرض الصورة]({user[7]})"
                )

                keyboard = [
                    [InlineKeyboardButton("❌ حظر", callback_data=f"ban_{user[0]}")],
                    [InlineKeyboardButton("❄️ تجميد", callback_data=f"freeze_{user[0]}")],
                    [InlineKeyboardButton("⭐ ترقية", callback_data=f"promote_{user[0]}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_profile_actions: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء تحميل الملف الشخصي. الرجاء المحاولة مرة أخرى.")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[1])
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET banned = 1 WHERE id = ?", (user_id,))
            await db.commit()
        await query.edit_message_text(f"✅ تم حظر المستخدم بنجاح.")
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء حظر المستخدم. الرجاء المحاولة مرة أخرى.")

async def freeze_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[1])
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET frozen = 1 WHERE id = ?", (user_id,))
            await db.commit()
        await query.edit_message_text(f"✅ تم تجميد المستخدم بنجاح.")
    except Exception as e:
        logger.error(f"Error freezing user: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء تجميد المستخدم. الرجاء المحاولة مرة أخرى.")

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[1])
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET admin = 1 WHERE id = ?", (user_id,))
            await db.commit()
        await query.edit_message_text(f"✅ تم ترقية المستخدم إلى مشرف بنجاح.")
    except Exception as e:
        logger.error(f"Error promoting user: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء ترقية المستخدم. الرجاء المحاولة مرة أخرى.")

async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT * FROM users")
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            df = pd.DataFrame(rows, columns=columns)
            excel_file = "users_data.xlsx"
            df.to_excel(excel_file, index=False)

            with open(excel_file, "rb") as file:
                await update.message.reply_document(document=file, caption="📊 بيانات المستخدمين")

            os.remove(excel_file)
            logger.info(f"User data exported by admin {user_id}.")
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تصدير بيانات المستخدمين. الرجاء المحاولة مرة أخرى.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    await update.message.reply_text("📢 الرجاء إرسال الرسالة التي تريد بثها:")
    context.user_data['awaiting_broadcast'] = True

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

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📝 الرجاء إرسال تعليقك:")
    return FEEDBACK

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    feedback_text = update.message.text.strip()
    if not feedback_text:
        await update.message.reply_text("❌ الرجاء إدخال تعليق صحيح.")
        return FEEDBACK

    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT INTO feedback (user_id, message) VALUES (?, ?)",
                (update.message.from_user.id, feedback_text)
            )
            await db.commit()

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

async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚨 الرجاء إرسال تقريرك:")
    return REPORT

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    report_text = update.message.text.strip()
    if not report_text:
        await update.message.reply_text("❌ الرجاء إدخال تقرير صحيح.")
        return REPORT

    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT INTO reports (user_id, message) VALUES (?, ?)",
                (update.message.from_user.id, report_text)
            )
            await db.commit()

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

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    try:
        args = update.message.text.split(maxsplit=2)
        if len(args) < 3:
            await update.message.reply_text("❌ الرجاء استخدام الصيغة الصحيحة: /reply <user_id> <message>")
            return

        target_user_id = int(args[1])
        message = args[2]

        await context.bot.send_message(chat_id=target_user_id, text=f"📨 رد من الإدارة:\n{message}")
        await update.message.reply_text(f"✅ تم إرسال الرد إلى المستخدم {target_user_id}.")
    except Exception as e:
        logger.error(f"Error in admin_reply: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إرسال الرد. الرجاء المحاولة مرة أخرى.")

async def import_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    if not update.message.document:
        await update.message.reply_text("❌ الرجاء إرسال ملف Excel.")
        return

    try:
        file = await context.bot.get_file(update.message.document.file_id)
        filename = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        await file.download_to_drive(filename)
        
        await update.message.reply_text("⏳ جاري استيراد البيانات...")
        
        df = pd.read_excel(filename)
        success_count = 0
        
        async with aiosqlite.connect(DATABASE) as db:
            for _, row in df.iterrows():
                try:
                    await db.execute(
                        """INSERT OR IGNORE INTO users 
                        (id, username, name, age, bio, type, location, 
                         photo, country, city, telegram_id, banned, frozen, admin)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            int(row['id']), str(row['username']), str(row['name']),
                            int(row['age']), str(row['bio']), str(row['type']),
                            str(row['location']), str(row['photo']), str(row['country']),
                            str(row['city']), int(row['telegram_id']),
                            int(row.get('banned', 0)), int(row.get('frozen', 0)), 
                            int(row.get('admin', 0))
                        )
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error importing user {row.get('username', '')}: {e}")
            
            await db.commit()
        
        os.remove(filename)
        await update.message.reply_text(
            f"✅ تم استيراد {success_count} من أصل {len(df)} مستخدم بنجاح!\n"
            f"تم تخطي {len(df) - success_count} مستخدم (موجودين مسبقاً)"
        )
    except Exception as e:
        logger.error(f"Import error: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء الاستيراد. الرجاء التأكد من صيغة الملف.")

async def extract_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    if not update.message.reply_to_message or not update.message.reply_to_message.forward_from_chat:
        await update.message.reply_text("❌ الرجاء عمل رد (reply) على رسالة من المجموعة التي تريد استخراج أعضائها.")
        return

    chat = update.message.reply_to_message.forward_from_chat
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ هذه ليست مجموعة. الرجاء تحديد مجموعة صحيحة.")
        return

    try:
        await update.message.reply_text(f"⏳ جاري استخراج أعضاء المجموعة: {chat.title}...")
        member_count = 0
        new_members = 0
        
        async with aiosqlite.connect(DATABASE) as db:
            async for member in context.bot.get_chat_members(chat.id):
                if member.user.is_bot:
                    continue
                    
                try:
                    cursor = await db.execute(
                        "SELECT 1 FROM group_members WHERE user_id = ? AND group_id = ?",
                        (member.user.id, chat.id)
                    )
                    exists = await cursor.fetchone()
                    
                    await db.execute(
                        """INSERT OR REPLACE INTO group_members 
                        (user_id, group_id, group_title, last_seen)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                        (member.user.id, chat.id, chat.title)
                    )
                    
                    result = await db.execute(
                        """INSERT OR IGNORE INTO users 
                        (id, username, name, telegram_id)
                        VALUES (?, ?, ?, ?)""",
                        (
                            member.user.id,
                            member.user.username or "",
                            member.user.full_name or "",
                            member.user.id
                        )
                    )
                    
                    if result.rowcount > 0:
                        new_members += 1
                    
                    member_count += 1
                    if member_count % 50 == 0:
                        await db.commit()
                except Exception as e:
                    logger.error(f"Error processing member {member.user.id}: {e}")
            
            await db.commit()
        
        await update.message.reply_text(
            f"✅ تم استخراج {member_count} عضو من المجموعة {chat.title}\n"
            f"تمت إضافة {new_members} عضو جديد إلى قاعدة البيانات"
        )
        
        keyboard = [[InlineKeyboardButton("📤 تصدير بيانات الأعضاء", callback_data=f"export_group_{chat.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("يمكنك تصدير بيانات الأعضاء الآن:", reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error extracting group members: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء استخراج الأعضاء. قد لا يكون لدي صلاحية رؤية الأعضاء.")

async def export_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.")
        return

    group_id = int(query.data.split('_')[2])
    
    try:
        await query.edit_message_text("⏳ جاري تجهيز البيانات للتصدير...")
        
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT group_title FROM group_members WHERE group_id = ? LIMIT 1",
                (group_id,)
            )
            group = await cursor.fetchone()
            group_title = group[0] if group else f"group_{group_id}"
            
            cursor = await db.execute(
                """SELECT u.id, u.username, u.name, u.age, u.bio, u.type, 
                   u.location, u.country, u.city, u.telegram_id
                FROM group_members gm
                JOIN users u ON gm.user_id = u.id
                WHERE gm.group_id = ?""",
                (group_id,)
            )
            members = await cursor.fetchall()
            
            if not members:
                await query.edit_message_text("❌ لا يوجد أعضاء مسجلين لهذه المجموعة.")
                return
            
            df = pd.DataFrame(members, columns=[
                'id', 'username', 'name', 'age', 'bio', 'type',
                'location', 'country', 'city', 'telegram_id'
            ])
            
            filename = f"members_{group_title}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            df.to_excel(filename, index=False)
            
            with open(filename, 'rb') as f:
                await context.bot.send_document(
                    chat_id=ADMIN_ID,
                    document=f,
                    caption=f"📊 أعضاء المجموعة {group_title} ({len(members)} عضو)"
                )
            
            os.remove(filename)
            
    except Exception as e:
        logger.error(f"Error exporting group members: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء تصدير البيانات.")

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await start(update, context)

async def set_bot_commands(application):
    commands = [
        ("start", "بدء التسجيل"),
        ("search", "البحث عن مستخدمين قريبين"),
        ("feedback", "إرسال تعليق"),
        ("report", "الإبلاغ عن مستخدم"),
    ]
    await application.bot.set_my_commands(commands)

    admin_commands = [
        ("admin", "لوحة التحكم"),
        ("export", "تصدير بيانات المستخدمين"),
        ("broadcast", "بث رسالة لجميع المستخدمين"),
        ("reply", "الرد على مستخدم"),
        ("import", "استيراد مستخدمين من ملف Excel"),
        ("extract", "استخراج أعضاء المجموعة")
    ]
    await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(ADMIN_ID))

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).get_updates_pool_timeout(30).build()

    # Registration handler
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

    # Feedback and report handlers
    feedback_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', feedback)],
        states={FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)]},
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )
    
    report_handler = ConversationHandler(
        entry_points=[CommandHandler('report', report_user)],
        states={REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report)]},
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )

    # Add all handlers
    handlers = [
        conv_handler,
        feedback_handler,
        report_handler,
        CommandHandler('search', show_nearby_profiles),
        CommandHandler('admin', admin_panel),
        CommandHandler('export', export_users),
        CommandHandler('broadcast', broadcast),
        CommandHandler('import', import_users),
        CommandHandler('extract', extract_group_members),
        CommandHandler('reply', admin_reply),
        CallbackQueryHandler(admin_profile_actions, pattern="^admin_profile_"),
        CallbackQueryHandler(ban_user, pattern="^ban_"),
        CallbackQueryHandler(freeze_user, pattern="^freeze_"),
        CallbackQueryHandler(promote_user, pattern="^promote_"),
        CallbackQueryHandler(export_group_members, pattern="^export_group_"),
        CallbackQueryHandler(main_menu, pattern="^main_menu$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast)
    ]
    
    for handler in handlers:
        application.add_handler(handler)

    # Set commands and run
    await set_bot_commands(application)
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(init_db())
    asyncio.run(main())
