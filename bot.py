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
    Bot
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

    # Create a menu with inline buttons in a grid layout
    keyboard = [
        [InlineKeyboardButton("بدء التسجيل", callback_data="agree_to_privacy")],
        [InlineKeyboardButton("المستخدمون القريبون", callback_data="nearby_users")],
        [InlineKeyboardButton("تعديل الملف الشخصي", callback_data="edit_profile")],
        [InlineKeyboardButton("الإبلاغ عن مستخدم", callback_data="report_user")],
        [InlineKeyboardButton("إرسال تعليق", callback_data="send_feedback")],
        [InlineKeyboardButton("تحديث", callback_data="refresh")],
        [InlineKeyboardButton("القائمة الرئيسية", callback_data="main_menu")]  # Main menu button
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the welcome message with the menu
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    logger.info("Start function completed.")
    return USERNAME

# Handle menu button clicks
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "nearby_users":
        await show_nearby_profiles(update, context)
    elif query.data == "edit_profile":
        await edit_profile(update, context)
    elif query.data == "report_user":
        await report_user(update, context)
    elif query.data == "send_feedback":
        await feedback(update, context)
    elif query.data == "refresh":
        await start(update, context)
    elif query.data == "main_menu":
        await start(update, context)

# Show nearby profiles (updated to handle callback_query)
async def show_nearby_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_location = context.user_data.get('location')
    if not user_location:
        await query.edit_message_text("❗ الرجاء التسجيل أولاً باستخدام /start لتحديد موقعك.")
        return

    user_coords = tuple(map(float, user_location.split(',')))
    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT * FROM users WHERE id != ? AND banned = 0", (update.effective_user.id,)) as cursor:
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
                    await query.edit_message_text("😔 لا يوجد مستخدمون مسجلون.")
                    return

                # Sort profiles by distance (nearest first)
                profiles.sort(key=lambda x: x['distance'])

                # Create a grid of profile cards
                profile_cards = []
                for profile in profiles[:50]:  # Show up to 50 profiles
                    profile_card = (
                        f"👤 الاسم: {profile['name']}\n"
                        f"📅 العمر: {profile['age']}\n"
                        f"🔄 النوع: {profile['type']}\n"
                        f"📍 المدينة: {profile['city']}, {profile['country']}\n"
                        f"📏 المسافة: {round(profile['distance'], 1)} كم\n"
                    )
                    if profile['photo']:
                        profile_card += f"📸 الصورة: [عرض الصورة]({profile['photo']})"
                    else:
                        profile_card += "📸 الصورة: غير متوفرة"
                    profile_cards.append(profile_card)

                if profile_cards:
                    # Send profiles as a grid of messages
                    for card in profile_cards:
                        if profile['photo']:
                            await query.message.reply_photo(
                                photo=profile['photo'],  # Send the profile picture
                                caption=card,
                                parse_mode="Markdown"
                            )
                        else:
                            await query.message.reply_text(card, parse_mode="Markdown")
                else:
                    await query.edit_message_text("😔 لم يتم العثور على ملفات قريبة.")
    except Exception as e:
        logger.error(f"Error in show_nearby_profiles: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء البحث. الرجاء المحاولة مرة أخرى.")

# Handle feedback (updated to handle callback_query)
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("📝 الرجاء إرسال تعليقك:")
    context.user_data['awaiting_feedback'] = True

# Handle report user (updated to handle callback_query)
async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("🚨 الرجاء إرسال تقريرك:")
    context.user_data['awaiting_report'] = True

# Handle text messages (for feedback and report)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('awaiting_feedback'):
        feedback_text = update.message.text
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"📝 تعليق جديد:\n{feedback_text}")
        await update.message.reply_text("✅ تم استلام تعليقك. شكراً لك!")
        context.user_data['awaiting_feedback'] = False
    elif context.user_data.get('awaiting_report'):
        report_text = update.message.text
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🚨 تقرير جديد:\n{report_text}")
        await update.message.reply_text("✅ تم استلام تقريرك. شكراً لك!")
        context.user_data['awaiting_report'] = False

# Main function
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).get_updates_pool_timeout(30).build()

    # Conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_username)],
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

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('search', show_nearby_profiles))
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CommandHandler('export', export_users))  # Add export command
    application.add_handler(CommandHandler('broadcast', broadcast))  # Add broadcast command
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))  # Add text handler
    application.add_handler(CallbackQueryHandler(view_profile, pattern="^profile_"))
    application.add_handler(CallbackQueryHandler(admin_profile_actions, pattern="^admin_profile_"))
    application.add_handler(CallbackQueryHandler(ban_user, pattern="^ban_"))
    application.add_handler(CallbackQueryHandler(freeze_user, pattern="^freeze_"))
    application.add_handler(CallbackQueryHandler(agree_to_privacy, pattern="^agree_to_privacy$"))
    application.add_handler(CallbackQueryHandler(handle_menu_buttons))  # Add handler for menu buttons

    # Set bot commands
    await set_bot_commands(application)

    # Run the bot
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(init_db())  # Initialize the database
    asyncio.run(main())
