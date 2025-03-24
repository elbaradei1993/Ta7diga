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
            await db.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# Start command (displays welcome message and starts registration)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Start function called.")
    user_id = update.message.from_user.id
    logger.info(f"User {user_id} started registration.")

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

            # Check if the user is already registered using their Telegram ID
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (update.message.from_user.id,))
            existing_user = await cursor.fetchone()
            if existing_user:
                await update.message.reply_text("❌ أنت مسجل بالفعل.")
                await show_nearby_profiles(update, context)
                return ConversationHandler.END
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

        # Log user data
        logger.info(f"User data: {context.user_data}")

        # Save user data to the database
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT OR REPLACE INTO users (id, username, name, age, bio, type, location, photo, country, city, telegram_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                 update.message.from_user.id)  # Store Telegram ID
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
                    distance = geodesic(user_coords, profile_coords).km  # Calculate distance in kilometers
                    profiles.append({
                        "id": row[0],
                        "name": row[2],
                        "age": row[3],
                        "type": row[5],
                        "city": row[9],
                        "country": row[8],
                        "photo": row[7],  # Add profile photo
                        "telegram_id": row[10],  # Add Telegram ID
                        "distance": distance
                    })

                if not profiles:
                    await update.message.reply_text("😔 لا يوجد مستخدمون مسجلون.")
                    return

                # Sort profiles by distance (nearest first)
                profiles.sort(key=lambda x: x['distance'])

                # Create a grid of profile cards
                for profile in profiles:
                    if profile['distance'] <= 50:  # Only show profiles within 50 km
                        profile_card = (
                            f"👤 الاسم: {profile['name']}\n"
                            f"📅 العمر: {profile['age']}\n"
                            f"🔄 النوع: {profile['type']}\n"
                            f"📍 المدينة: {profile['city']}, {profile['country']}\n"
                            f"📏 المسافة: {round(profile['distance'], 1)} كم\n"
                            f"📸 الصورة: [عرض الصورة]({profile['photo']})"
                        )

                        # Add a "Send Message" button
                        keyboard = [
                            [InlineKeyboardButton("📩 إرسال رسالة", url=f"tg://user?id={profile['telegram_id']}")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        await update.message.reply_text(profile_card, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error showing nearby profiles: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء عرض الملفات القريبة.")

# Feedback command
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📝 الرجاء إرسال ملاحظاتك:")
    return FEEDBACK

# Report command
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚨 الرجاء إرسال تقريرك:")
    return REPORT

# Handle feedback submission
async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    feedback_text = update.message.text.strip()
    user_id = update.message.from_user.id

    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("INSERT INTO feedback (user_id, feedback_text) VALUES (?, ?)", (user_id, feedback_text))
            await db.commit()

        await update.message.reply_text("✅ تم إرسال ملاحظاتك بنجاح!")

        # Send feedback to admin
        feedback_message = f"📝 ملاحظات جديدة من المستخدم {user_id}:\n{feedback_text}"
        admin_keyboard = [[InlineKeyboardButton("رد", callback_data=f"reply_feedback_{user_id}")]]
        admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)
        await context.bot.send_message(chat_id=ADMIN_ID, text=feedback_message, reply_markup=admin_reply_markup)

        return ConversationHandler.END  # End the conversation
    except Exception as e:
        logger.error(f"Error handling feedback: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إرسال ملاحظاتك. الرجاء المحاولة مرة أخرى.")
        return ConversationHandler.END

# Handle report submission
async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    report_text = update.message.text.strip()
    user_id = update.message.from_user.id

    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("INSERT INTO reports (user_id, report_text) VALUES (?, ?)", (user_id, report_text))
            await db.commit()

        await update.message.reply_text("✅ تم إرسال تقريرك بنجاح!")

        # Send report to admin
        report_message = f"🚨 تقرير جديد من المستخدم {user_id}:\n{report_text}"
        admin_keyboard = [[InlineKeyboardButton("رد", callback_data=f"reply_report_{user_id}")]]
        admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)
        await context.bot.send_message(chat_id=ADMIN_ID, text=report_message, reply_markup=admin_reply_markup)

        return ConversationHandler.END  # End the conversation
    except Exception as e:
        logger.error(f"Error handling report: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إرسال تقريرك. الرجاء المحاولة مرة أخرى.")
        return ConversationHandler.END

# Admin reply to feedback/report
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    if "reply_feedback" in data:
        user_id = data.split('_')[-1]
        context.user_data['reply_to'] = user_id
        context.user_data['reply_type'] = 'feedback'
        await query.message.reply_text(f"📝 الرجاء إرسال ردك إلى المستخدم {user_id}:")
        return

    elif "reply_report" in data:
        user_id = data.split('_')[-1]
        context.user_data['reply_to'] = user_id
        context.user_data['reply_type'] = 'report'
        await query.message.reply_text(f"🚨 الرجاء إرسال ردك إلى المستخدم {user_id}:")
        return

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_text = update.message.text.strip()
    user_id = context.user_data.get('reply_to')
    reply_type = context.user_data.get('reply_type')

    if not user_id or not reply_type:
        await update.message.reply_text("❌ لم يتم العثور على المستخدم.")
        return

    try:
        await context.bot.send_message(chat_id=user_id, text=f"✉️ رد من الأدمن:\n{reply_text}")
        await update.message.reply_text("✅ تم إرسال الرد بنجاح!")

        # Clear the context data
        context.user_data['reply_to'] = None
        context.user_data['reply_type'] = None

    except Exception as e:
        logger.error(f"Error sending admin reply: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إرسال الرد.")

# Admin command to export users to Excel
async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية لتنفيذ هذا الأمر.")
        return

    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT * FROM users") as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await update.message.reply_text("😔 لا يوجد مستخدمون مسجلون.")
            return

        # Convert data to DataFrame
        df = pd.DataFrame(rows, columns=[
            "ID", "Username", "Name", "Age", "Bio", "Type", "Location", "Photo", "Country", "City", "Telegram ID", "Banned", "Frozen", "Admin"
        ])

        # Export to Excel
        excel_file = "users.xlsx"
        df.to_excel(excel_file, index=False)

        # Send the Excel file to the admin
        await context.bot.send_document(chat_id=ADMIN_ID, document=open(excel_file, 'rb'))
        await update.message.reply_text("✅ تم تصدير بيانات المستخدمين إلى ملف Excel.")

        # Remove the file
        os.remove(excel_file)

    except Exception as e:
        logger.error(f"Error exporting users: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تصدير بيانات المستخدمين.")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    try:
        await update.message.reply_text("❌ حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى.")
    except Exception as e:
        logger.error(f"Error sending error message: {e}")

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "مرحبًا بك في بوت تحديقة!\n\n"
        "/start - لبدء أو إعادة عملية التسجيل.\n"
        "/feedback - لإرسال ملاحظاتك واقتراحاتك.\n"
        "/report - لتقديم تقرير عن مشكلة أو مخالفة.\n"
        "/nearby - لعرض الملفات الشخصية القريبة منك.\n"
    )
    if update.message.from_user.id == ADMIN_ID:
        help_text += (
            "\n--- أوامر المسؤول ---"
            "\n/export_users - لتصدير بيانات المستخدمين إلى ملف Excel."
        )
    await update.message.reply_text(help_text)

# Main function
def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Initialize database
    asyncio.run(init_db())

    # Conversation handler for registration
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_username)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_age)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_bio)],
            TYPE: [CallbackQueryHandler(set_type, pattern=r"^(سالب|موجب|مبادل)$")],
            COUNTRY: [CallbackQueryHandler(set_country, pattern=r"^country_")],
            CITY: [CallbackQueryHandler(set_city, pattern=r"^city_")],
            LOCATION: [MessageHandler(filters.LOCATION, set_location)],
            PHOTO: [MessageHandler(filters.PHOTO, set_photo)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Conversation handler for feedback
    feedback_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", feedback)],
        states={
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Conversation handler for report
    report_handler = ConversationHandler(
        entry_points=[CommandHandler("report", report)],
        states={
            REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Command handlers
    app.add_handler(registration_handler)
    app.add_handler(feedback_handler)
    app.add_handler(report_handler)
    app.add_handler(CommandHandler("nearby", show_nearby_profiles))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(admin_reply, pattern=r"^(reply_feedback|reply_report)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_reply))

    # Admin command handler
    app.add_handler(CommandHandler("export_users", export_users))

    # Error handler
    app.add_error_handler(error_handler)

    # Run the bot
    app.run_polling()

if __name__ == '__main__':
    main()
