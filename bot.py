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

# [Previous functions remain unchanged until main()]

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
                    # Check if member already exists
                    cursor = await db.execute(
                        "SELECT 1 FROM group_members WHERE user_id = ? AND group_id = ?",
                        (member.user.id, chat.id)
                    )
                    exists = await cursor.fetchone()
                    
                    # Update or insert group membership
                    await db.execute(
                        """INSERT OR REPLACE INTO group_members 
                        (user_id, group_id, group_title, last_seen)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                        (member.user.id, chat.id, chat.title)
                    )
                    
                    # Add basic user info if not exists
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
        
        # Offer export option
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
            # Get group info
            cursor = await db.execute(
                "SELECT group_title FROM group_members WHERE group_id = ? LIMIT 1",
                (group_id,)
            )
            group = await cursor.fetchone()
            group_title = group[0] if group else f"group_{group_id}"
            
            # Get all members
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
            
            # Create DataFrame
            df = pd.DataFrame(members, columns=[
                'id', 'username', 'name', 'age', 'bio', 'type',
                'location', 'country', 'city', 'telegram_id'
            ])
            
            # Save to Excel
            filename = f"members_{group_title}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            df.to_excel(filename, index=False)
            
            # Send the file
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

async def set_bot_commands(application):
    # User commands
    commands = [
        ("start", "بدء التسجيل"),
        ("search", "البحث عن مستخدمين قريبين"),
        ("feedback", "إرسال تعليق"),
        ("report", "الإبلاغ عن مستخدم"),
    ]
    await application.bot.set_my_commands(commands)

    # Admin commands
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
