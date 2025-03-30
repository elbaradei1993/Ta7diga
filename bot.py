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
from io import BytesIO
import re

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
BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

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
    """Initialize database with proper error handling and migrations"""
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            
            # Create tables if they don't exist
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    user_id INTEGER,
                    group_id INTEGER,
                    group_title TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, group_id),
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )""")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )""")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    reported_user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id),
                    FOREIGN KEY (reported_user_id) REFERENCES users(telegram_id)
                )""")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    target_id INTEGER,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES users(telegram_id)
                )""")
            
            # Add any missing columns (for migrations)
            await migrate_database(db)
            
            await db.commit()
            logger.info("Database initialized successfully.")
            
            # Create backup
            await backup_database()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

async def migrate_database(db):
    """Handle database schema migrations"""
    # Check if columns exist and add them if missing
    columns_to_check = [
        ('users', 'banned', 'INTEGER DEFAULT 0'),
        ('users', 'frozen', 'INTEGER DEFAULT 0'),
        ('users', 'admin', 'INTEGER DEFAULT 0'),
        ('reports', 'reported_user_id', 'INTEGER')
    ]
    
    for table, column, col_type in columns_to_check:
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            logger.info(f"Added column {column} to {table}")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" not in str(e):
                logger.error(f"Error adding column {column} to {table}: {e}")

async def backup_database():
    """Create a backup of the database"""
    backup_file = os.path.join(BACKUP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    try:
        async with aiosqlite.connect(DATABASE) as src:
            async with aiosqlite.connect(backup_file) as dst:
                await src.backup(dst)
        logger.info(f"Database backup created: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        return None

async def log_admin_action(admin_id: int, action: str, target_id: int = None, details: str = None):
    """Log admin actions for audit trail"""
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (?, ?, ?, ?)",
                (admin_id, action, target_id, details)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Error logging admin action: {e}")

async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    if user_id == ADMIN_ID:  # Always allow the main admin
        return True
        
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT admin FROM users WHERE telegram_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            return result and result[0] == 1
    except Exception as e:
        logger.error(f"Error checking admin status for {user_id}: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    # Check if user already exists and is not banned/frozen
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT banned, frozen FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            user_status = await cursor.fetchone()
            
            if user_status:
                if user_status[0]:  # banned
                    await update.message.reply_text("❌ حسابك محظور. لا يمكنك استخدام البوت.")
                    return ConversationHandler.END
                elif user_status[1]:  # frozen
                    await update.message.reply_text("❄️ حسابك مجمد مؤقتًا. الرجاء التواصل مع الإدارة.")
                    return ConversationHandler.END
                else:
                    await update.message.reply_text(
                        "مرحبًا بك مرة أخرى! يمكنك استخدام /search للبحث عن أشخاص قريبين."
                    )
                    return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error checking user registration: {e}")
    
    # If not registered, show terms
    keyboard = [
        [InlineKeyboardButton("✅ الموافقة على الشروط", callback_data="agree_to_privacy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"مرحبًا {user.mention_html()}!\n\n"
        "أهلاً بك في بوت التعارف السوداني. للبدء، يرجى الموافقة على الشروط والأحكام."
    )
    
    await update.message.reply_html(
        welcome_text,
        reply_markup=reply_markup
    )
    return USERNAME

async def agree_to_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user agrees to privacy policy"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "شكرًا لموافقتك على الشروط.\n\n"
        "الرجاء إرسال اسم المستخدم الخاص بك (بدون @):"
    )
    return USERNAME

async def set_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store username and ask for name"""
    username = update.message.text.strip()
    
    # Validate username
    if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
        await update.message.reply_text(
            "اسم المستخدم غير صحيح. يجب أن يحتوي على حروف وأرقام وشرطة سفلية فقط (5-32 حرف)."
        )
        return USERNAME
    
    # Check if username exists
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (username,)
        )
        exists = await cursor.fetchone()
    
    if exists:
        await update.message.reply_text("اسم المستخدم هذا مستخدم بالفعل. الرجاء اختيار اسم آخر.")
        return USERNAME
    
    context.user_data['username'] = username
    
    await update.message.reply_text(
        "تم حفظ اسم المستخدم.\n\n"
        "الرجاء إرسال اسمك الكامل:"
    )
    return NAME

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store name and ask for age"""
    name = update.message.text.strip()
    
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text("الاسم يجب أن يكون بين 2 و50 حرفًا.")
        return NAME
    
    context.user_data['name'] = name
    
    await update.message.reply_text(
        "تم حفظ الاسم.\n\n"
        "الرجاء إرسال عمرك:"
    )
    return AGE

async def set_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store age and ask for bio"""
    try:
        age = int(update.message.text)
        if age < 18 or age > 100:
            await update.message.reply_text("الرجاء إدخال عمر بين 18 و100")
            return AGE
        
        context.user_data['age'] = age
        
        await update.message.reply_text(
            "تم حفظ العمر.\n\n"
            "الرجاء إرسال نبذة قصيرة عنك:"
        )
        return BIO
    except ValueError:
        await update.message.reply_text("الرجاء إدخال رقم صحيح للعمر")
        return AGE

async def set_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store bio and ask for type"""
    bio = update.message.text.strip()
    
    if len(bio) < 10 or len(bio) > 500:
        await update.message.reply_text("النبذة يجب أن تكون بين 10 و500 حرف.")
        return BIO
    
    context.user_data['bio'] = bio
    
    keyboard = [
        [InlineKeyboardButton("👨 رجل", callback_data="male")],
        [InlineKeyboardButton("👩 امرأة", callback_data="female")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "تم حفظ النبذة.\n\n"
        "الرجاء تحديد جنسك:",
        reply_markup=reply_markup
    )
    return TYPE

async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store type and ask for country"""
    query = update.callback_query
    await query.answer()
    
    user_type = query.data
    context.user_data['type'] = user_type
    
    keyboard = [
        [InlineKeyboardButton(country, callback_data=f"country_{country}")]
        for country in COUNTRIES.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "تم حفظ الجنس.\n\n"
        "الرجاء تحديد بلدك:",
        reply_markup=reply_markup
    )
    return COUNTRY

async def set_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store country and ask for city"""
    query = update.callback_query
    await query.answer()
    
    country = query.data.replace("country_", "")
    context.user_data['country'] = country
    
    cities = COUNTRIES.get(country, [])
    keyboard = [
        [InlineKeyboardButton(city, callback_data=f"city_{city}")]
        for city in cities
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"تم حفظ البلد ({country}).\n\n"
        "الرجاء تحديد مدينتك:",
        reply_markup=reply_markup
    )
    return CITY

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store city and ask for location"""
    query = update.callback_query
    await query.answer()
    
    city = query.data.replace("city_", "")
    context.user_data['city'] = city
    
    await query.edit_message_text(
        f"تم حفظ المدينة ({city}).\n\n"
        "الرجاء مشاركة موقعك الجغرافي:"
    )
    return LOCATION

async def set_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store location and ask for photo"""
    location = update.message.location
    context.user_data['location'] = f"{location.latitude},{location.longitude}"
    
    await update.message.reply_text(
        "تم حفظ الموقع.\n\n"
        "الرجاء إرسال صورتك:"
    )
    return PHOTO

async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store photo and complete registration"""
    photo = update.message.photo[-1].file_id
    context.user_data['photo'] = photo
    
    # Save all data to database
    user_data = context.user_data
    user = update.effective_user
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                """INSERT INTO users (
                    username, name, age, bio, type, 
                    location, photo, country, city, telegram_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_data.get('username'),
                    user_data.get('name'),
                    user_data.get('age'),
                    user_data.get('bio'),
                    user_data.get('type'),
                    user_data.get('location'),
                    user_data.get('photo'),
                    user_data.get('country'),
                    user_data.get('city'),
                    user.id
                )
            )
            await db.commit()
            
        await update.message.reply_text(
            "🎉 تم تسجيل بياناتك بنجاح!\n\n"
            "يمكنك الآن استخدام الأمر /search للبحث عن أشخاص قريبين منك."
        )
        
        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 New user registered:\n\n"
                 f"Name: {user_data.get('name')}\n"
                 f"Age: {user_data.get('age')}\n"
                 f"Location: {user_data.get('city')}, {user_data.get('country')}\n"
                 f"Username: @{user_data.get('username')}"
        )
    except Exception as e:
        logger.error(f"Error saving user: {e}")
        await update.message.reply_text(
            "❌ حدث خطأ أثناء حفظ بياناتك. الرجاء المحاولة لاحقًا."
        )
    
    return ConversationHandler.END

async def show_nearby_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show nearby profiles to the user"""
    user = update.effective_user
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Check if user is registered
            cursor = await db.execute(
                "SELECT 1 FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            if not await cursor.fetchone():
                await update.message.reply_text(
                    "❌ لم تقم بتسجيل بياناتك بعد. الرجاء استخدام /start لتسجيل بياناتك أولاً."
                )
                return
            
            # Check if user is banned or frozen
            cursor = await db.execute(
                "SELECT banned, frozen FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            user_status = await cursor.fetchone()
            
            if user_status and (user_status[0] or user_status[1]):
                await update.message.reply_text(
                    "❌ حسابك محظور أو مجمد. لا يمكنك استخدام هذه الميزة."
                )
                return
            
            # Get user's location
            cursor = await db.execute(
                "SELECT location FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            user_location = await cursor.fetchone()
            
            if not user_location or not user_location[0]:
                await update.message.reply_text(
                    "❌ لم تقم بمشاركة موقعك بعد. الرجاء استخدام /start لتسجيل بياناتك."
                )
                return
            
            lat, lon = map(float, user_location[0].split(','))
            
            # Get all nearby users (within 50km)
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id != ? AND banned = 0 AND frozen = 0",
                (user.id,)
            )
            users = await cursor.fetchall()
            
            nearby_users = []
            for u in users:
                if not u[6]:  # Skip if no location
                    continue
                
                u_lat, u_lon = map(float, u[6].split(','))
                distance = geodesic((lat, lon), (u_lat, u_lon)).km
                
                if distance <= 50:
                    nearby_users.append((u, distance))
            
            if not nearby_users:
                await update.message.reply_text("❌ لا يوجد أشخاص قريبين منك الآن.")
                return
            
            # Sort by distance and show top 10
            nearby_users.sort(key=lambda x: x[1])
            
            for u, distance in nearby_users[:10]:
                caption = (
                    f"👤 {u[2]}, {u[3]} سنة\n"
                    f"📍 {u[8]}, {u[9]} (على بعد {distance:.1f} كم)\n"
                    f"📝 {u[4]}\n\n"
                    f"✉️ @{u[1]}"
                )
                
                try:
                    await context.bot.send_photo(
                        chat_id=user.id,
                        photo=u[7],
                        caption=caption,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🚀 إرسال رسالة", url=f"https://t.me/{u[1]}")]
                        ])
                    )
                except telegram.error.BadRequest:
                    await update.message.reply_text(
                        caption,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🚀 إرسال رسالة", url=f"https://t.me/{u[1]}")]
                        ])
                    )
                
    except Exception as e:
        logger.error(f"Error showing nearby profiles: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء البحث. الرجاء المحاولة لاحقًا.")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start feedback conversation"""
    await update.message.reply_text(
        "📝 الرجاء إرسال ملاحظاتك أو اقتراحاتك:\n\n"
        "يمكنك إرسال /cancel لإلغاء الأمر."
    )
    return FEEDBACK

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user feedback"""
    feedback_text = update.message.text
    user = update.effective_user
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT INTO feedback (user_id, message) VALUES (?, ?)",
                (user.id, feedback_text)
            )
            await db.commit()
            
        # Get username or use user ID if username is None
        username = f"@{user.username}" if user.username else f"user_{user.id}"
            
        await update.message.reply_text(
            "شكرًا لك على ملاحظاتك! سنقوم بمراجعتها قريبًا."
        )
        
        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📝 ملاحظات جديدة من {username}:\n\n{feedback_text}"
        )
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حفظ ملاحظاتك. الرجاء المحاولة لاحقًا.")
    
    return ConversationHandler.END

async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start report conversation"""
    await update.message.reply_text(
        "⚠️ الرجاء إرسال تقريرك عن المستخدم (مع ذكر اسم المستخدم @username):\n\n"
        "يمكنك إرسال /cancel لإلغاء الأمر."
    )
    return REPORT

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user report"""
    if update.message.text == '/cancel':
        await update.message.reply_text("تم إلغاء عملية الإبلاغ.")
        return ConversationHandler.END
    
    report_text = update.message.text
    user = update.effective_user
    
    # Extract username from report
    username_match = re.search(r'@([a-zA-Z0-9_]{5,32})', report_text)
    if not username_match:
        await update.message.reply_text("❌ الرجاء ذكر اسم المستخدم في التقرير (مثال: @username)")
        return REPORT
    
    username = username_match.group(1)
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Get reported user ID
            cursor = await db.execute(
                "SELECT telegram_id FROM users WHERE username = ?",
                (username,)
            )
            reported_user = await cursor.fetchone()
            
            if not reported_user:
                await update.message.reply_text("❌ لم يتم العثور على المستخدم المبلغ عنه")
                return REPORT
            
            await db.execute(
                "INSERT INTO reports (user_id, reported_user_id, message) VALUES (?, ?, ?)",
                (user.id, reported_user[0], report_text)
            )
            await db.commit()
            
        await update.message.reply_text(
            "شكرًا لك على التقرير! سنقوم بمراجعته قريبًا."
        )
        
        # Notify admin
        reporter_username = f"@{user.username}" if user.username else f"user_{user.id}"
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ تقرير جديد من {reporter_username}:\n\n"
                 f"المبلغ عنه: @{username}\n"
                 f"التقرير:\n{report_text}"
        )
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حفظ تقريرك. الرجاء المحاولة لاحقًا.")
    
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel with working buttons"""
    user = update.effective_user
    if user.id != ADMIN_ID and not await is_admin(user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول إلى لوحة التحكم.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👤 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📤 تصدير البيانات", callback_data="admin_export")],
        [InlineKeyboardButton("📥 استيراد البيانات", callback_data="admin_import")],
        [InlineKeyboardButton("📢 بث رسالة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💾 إنشاء نسخة احتياطية", callback_data="admin_backup")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠 لوحة التحكم الإدارية:",
        reply_markup=reply_markup
    )

# [Rest of the admin functions remain the same...]

async def main():
    # Initialize database
    await init_db()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()

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

    # [Rest of the handler setup remains the same...]

    # Add all handlers
    application.add_handler(conv_handler)
    application.add_handler(feedback_handler)
    application.add_handler(report_handler)
    application.add_handler(CommandHandler('search', show_nearby_profiles))
    application.add_handler(CommandHandler('admin', admin_panel))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
