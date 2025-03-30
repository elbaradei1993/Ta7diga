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

# Database Lock for thread safety
db_lock = asyncio.Lock()

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
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT admin FROM users WHERE telegram_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            return result and result[0] == 1
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    # Check if user already exists
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT 1 FROM users WHERE telegram_id = ?",
            (user.id,)
        )
        exists = await cursor.fetchone()
    
    if exists:
        await update.message.reply_text(
            "مرحبًا بك مرة أخرى! يمكنك استخدام /search للبحث عن أشخاص قريبين."
        )
        return ConversationHandler.END
    
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
            
        await update.message.reply_text(
            "شكرًا لك على ملاحظاتك! سنقوم بمراجعتها قريبًا."
        )
        
        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📝 ملاحظات جديدة من @{user.username}:\n\n{feedback_text}"
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
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ تقرير جديد من @{user.username}:\n\n"
                 f"المبلغ عنه: @{username}\n"
                 f"التقرير:\n{report_text}"
        )
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حفظ تقريرك. الرجاء المحاولة لاحقًا.")
    
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel with working buttons"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only command")
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

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Get counts in a single transaction
            await db.execute("BEGIN")
            
            # Get total users
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]
            
            # Get active users
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE banned = 0 AND frozen = 0")
            active_users = (await cursor.fetchone())[0]
            
            # Get banned users
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
            banned_users = (await cursor.fetchone())[0]
            
            # Get frozen accounts
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE frozen = 1")
            frozen_users = (await cursor.fetchone())[0]
            
            # Get admins
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE admin = 1")
            admin_users = (await cursor.fetchone())[0]
            
            # Get feedback count
            cursor = await db.execute("SELECT COUNT(*) FROM feedback")
            feedback_count = (await cursor.fetchone())[0]
            
            # Get reports count
            cursor = await db.execute("SELECT COUNT(*) FROM reports")
            reports_count = (await cursor.fetchone())[0]
            
            await db.commit()
            
            stats_text = (
                f"📊 إحصائيات البوت:\n\n"
                f"👥 إجمالي المستخدمين: {total_users}\n"
                f"🟢 مستخدمين نشطين: {active_users}\n"
                f"🔴 مستخدمين محظورين: {banned_users}\n"
                f"❄️ حسابات مجمدة: {frozen_users}\n"
                f"👑 مدراء: {admin_users}\n"
                f"📝 ملاحظات: {feedback_count}\n"
                f"⚠️ تقارير: {reports_count}"
            )
            
            keyboard = [
                [InlineKeyboardButton("↩️ رجوع", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                stats_text,
                reply_markup=reply_markup
            )
            
            await log_admin_action(query.from_user.id, "view_stats")
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء جلب الإحصائيات")

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user management options"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    keyboard = [
        [InlineKeyboardButton("🔍 عرض مستخدم", callback_data="admin_view_user")],
        [InlineKeyboardButton("⛔ حظر مستخدم", callback_data="admin_ban_user")],
        [InlineKeyboardButton("❄️ تجميد مستخدم", callback_data="admin_freeze_user")],
        [InlineKeyboardButton("👑 ترقية مستخدم", callback_data="admin_promote_user")],
        [InlineKeyboardButton("📋 قائمة المستخدمين", callback_data="admin_list_users_1")],
        [InlineKeyboardButton("↩️ رجوع", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👤 إدارة المستخدمين:",
        reply_markup=reply_markup
    )

async def admin_view_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View user details"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "الرجاء إرسال معرف المستخدم (ID) أو اسم المستخدم (@username):"
    )
    return "view_user"

async def handle_view_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle viewing user details"""
    if not await is_admin(update.message.from_user.id):
        return
    
    user_input = update.message.text.strip()
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            if user_input.startswith('@'):
                cursor = await db.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (user_input[1:],)
                )
            else:
                try:
                    user_id = int(user_input)
                    cursor = await db.execute(
                        "SELECT * FROM users WHERE telegram_id = ? OR id = ?",
                        (user_id, user_id)
                    )
                except ValueError:
                    await update.message.reply_text("❌ الرجاء إدخال معرف صحيح أو اسم مستخدم")
                    return "view_user"
            
            user = await cursor.fetchone()
            
            if not user:
                await update.message.reply_text("❌ لم يتم العثور على المستخدم")
                return "view_user"
            
            user_details = (
                f"👤 معلومات المستخدم:\n\n"
                f"🆔 ID: {user[0]}\n"
                f"📱 Telegram ID: {user[10]}\n"
                f"👤 اسم المستخدم: @{user[1]}\n"
                f"🏷 الاسم: {user[2]}\n"
                f"🎂 العمر: {user[3]}\n"
                f"📝 النبذة: {user[4]}\n"
                f"👫 الجنس: {user[5]}\n"
                f"📍 الموقع: {user[6]}\n"
                f"🌍 البلد: {user[8]}\n"
                f"🏙 المدينة: {user[9]}\n"
                f"⛔ حالة الحظر: {'نعم' if user[11] else 'لا'}\n"
                f"❄️ حالة التجميد: {'نعم' if user[12] else 'لا'}\n"
                f"👑 حالة المدير: {'نعم' if user[13] else 'لا'}\n"
                f"📅 تاريخ التسجيل: {user[14]}"
            )
            
            keyboard = [
                [InlineKeyboardButton("⛔ حظر", callback_data=f"ban_{user[10]}")],
                [InlineKeyboardButton("❄️ تجميد", callback_data=f"freeze_{user[10]}")],
                [InlineKeyboardButton("👑 ترقية", callback_data=f"promote_{user[10]}")],
                [InlineKeyboardButton("↩️ رجوع", callback_data="admin_users")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await context.bot.send_photo(
                    chat_id=update.message.from_user.id,
                    photo=user[7],
                    caption=user_details,
                    reply_markup=reply_markup
                )
            except telegram.error.BadRequest:
                await update.message.reply_text(
                    user_details,
                    reply_markup=reply_markup
                )
            
            await log_admin_action(update.message.from_user.id, "view_user", user[10])
            
    except Exception as e:
        logger.error(f"Error viewing user: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء جلب معلومات المستخدم")
    
    return ConversationHandler.END

async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List users with pagination"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    page = int(query.data.split('_')[-1])
    limit = 10
    offset = (page - 1) * limit
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Get total count
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]
            
            # Get paginated users
            cursor = await db.execute(
                "SELECT id, username, name, banned, frozen, admin FROM users LIMIT ? OFFSET ?",
                (limit, offset)
            )
            users = await cursor.fetchall()
            
            if not users:
                await query.edit_message_text("❌ لا يوجد مستخدمين لعرضهم")
                return
            
            users_text = "\n".join(
                f"{u[0]}. @{u[1]} - {u[2]} "
                f"{'⛔' if u[3] else ''}"
                f"{'❄️' if u[4] else ''}"
                f"{'👑' if u[5] else ''}"
                for u in users
            )
            
            # Create pagination buttons
            total_pages = (total_users + limit - 1) // limit
            buttons = []
            
            if page > 1:
                buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"admin_list_users_{page-1}"))
            
            buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
            
            if page < total_pages:
                buttons.append(InlineKeyboardButton("➡️ التالي", callback_data=f"admin_list_users_{page+1}"))
            
            keyboard = [
                buttons,
                [InlineKeyboardButton("🔍 عرض مستخدم", callback_data="admin_view_user")],
                [InlineKeyboardButton("↩️ رجوع", callback_data="admin_users")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"📋 قائمة المستخدمين (الصفحة {page} من {total_pages}):\n\n"
                f"{users_text}",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء جلب قائمة المستخدمين")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast conversation with confirmation"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    await update.message.reply_text(
        "📢 الرجاء إرسال الرسالة التي تريد بثها لجميع المستخدمين:\n\n"
        "يمكنك إرسال /cancel لإلغاء الأمر."
    )
    return "broadcast"

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message with confirmation"""
    if not await is_admin(update.message.from_user.id):
        return
    
    message = update.message.text
    if not message:
        await update.message.reply_text("❌ الرسالة فارغة")
        return "broadcast"
    
    context.user_data['broadcast_message'] = message
    
    # Get estimated user count
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE banned = 0 AND frozen = 0")
        count = (await cursor.fetchone())[0]
    
    keyboard = [
        [InlineKeyboardButton(f"✅ تأكيد البث ({count} مستخدم)", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ هل أنت متأكد من أنك تريد بث هذه الرسالة لجميع المستخدمين؟\n\n"
        f"محتوى الرسالة:\n{message}",
        reply_markup=reply_markup
    )
    return "confirm_broadcast"

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute broadcast"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    if query.data == "confirm_broadcast":
        message = context.user_data.get('broadcast_message')
        
        try:
            async with aiosqlite.connect(DATABASE) as db:
                cursor = await db.execute("SELECT telegram_id FROM users WHERE banned = 0 AND frozen = 0")
                users = await cursor.fetchall()
                
            success = 0
            failed = 0
            failed_users = []
            
            await query.edit_message_text("⏳ جاري إرسال الرسالة...")
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user[0],
                        text=message
                    )
                    success += 1
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error sending to {user[0]}: {e}")
                    failed += 1
                    failed_users.append(str(user[0]))
            
            report = (
                f"✅ تم إرسال الرسالة إلى {success} مستخدم\n"
                f"❌ فشل الإرسال إلى {failed} مستخدم"
            )
            
            if failed > 0:
                report += f"\n\nالمستخدمين الذين فشل الإرسال لهم:\n{', '.join(failed_users[:10])}"
                if len(failed_users) > 10:
                    report += f"\nو {len(failed_users)-10} أكثر..."
            
            await query.edit_message_text(report)
            
            await log_admin_action(
                query.from_user.id, 
                "broadcast", 
                details=f"Sent to {success}, failed {failed}"
            )
            
        except Exception as e:
            logger.error(f"Error broadcasting: {e}")
            await query.edit_message_text("❌ حدث خطأ أثناء البث. الرجاء المحاولة لاحقًا.")
    else:
        await query.edit_message_text("❌ تم إلغاء عملية البث")
    
    return ConversationHandler.END

async def extract_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract members from a group with confirmation"""
    if not await is_admin(update.message.from_user.id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    if not update.message.reply_to_message or not update.message.reply_to_message.forward_from_chat:
        await update.message.reply_text("❌ الرجاء إعادة توجيه رسالة من المجموعة")
        return
    
    group = update.message.reply_to_message.forward_from_chat
    if group.type != "supergroup":
        await update.message.reply_text("❌ هذه ليست مجموعة")
        return
    
    context.user_data['extract_group'] = group
    
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد الاستخراج", callback_data="confirm_extract")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_extract")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ هل أنت متأكد من أنك تريد استخراج أعضاء مجموعة {group.title}?\n\n"
        "هذه العملية قد تستغرق بعض الوقت.",
        reply_markup=reply_markup
    )
    return "confirm_extract"

async def confirm_extract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute group member extraction"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    if query.data == "confirm_extract":
        group = context.user_data.get('extract_group')
        
        try:
            await query.edit_message_text(f"⏳ جاري استخراج أعضاء {group.title}...")
            
            members = []
            async for member in context.bot.get_chat_members(group.id):
                if member.user.is_bot:
                    continue
                
                members.append((
                    member.user.id,
                    member.user.username or "",
                    member.user.full_name,
                    group.id,
                    group.title
                ))
            
            async with aiosqlite.connect(DATABASE) as db:
                await db.executemany(
                    """INSERT OR REPLACE INTO group_members 
                    (user_id, group_id, group_title) 
                    VALUES (?, ?, ?)""",
                    [(m[0], m[3], m[4]) for m in members]
                )
                await db.commit()
            
            await query.edit_message_text(
                f"✅ تم حفظ {len(members)} عضو من {group.title}"
            )
            
            await log_admin_action(
                query.from_user.id, 
                "extract_members", 
                details=f"Extracted {len(members)} from {group.title}"
            )
            
        except Exception as e:
            logger.error(f"Error extracting members: {e}")
            await query.edit_message_text("❌ حدث خطأ أثناء استخراج الأعضاء. الرجاء المحاولة لاحقًا.")
    else:
        await query.edit_message_text("❌ تم إلغاء عملية الاستخراج")
    
    return ConversationHandler.END

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin reply to user with confirmation"""
    if not await is_admin(update.message.from_user.id):
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("❌ الاستخدام: /reply <user_id> <message>")
        return
    
    user_id = int(context.args[0])
    message = " ".join(context.args[1:])
    
    context.user_data['admin_reply'] = {
        'user_id': user_id,
        'message': message
    }
    
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="confirm_reply")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_reply")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ هل أنت متأكد من أنك تريد إرسال هذه الرسالة إلى المستخدم {user_id}?\n\n"
        f"محتوى الرسالة:\n{message}",
        reply_markup=reply_markup
    )
    return "confirm_reply"

async def confirm_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and send admin reply"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    if query.data == "confirm_reply":
        reply_data = context.user_data.get('admin_reply')
        
        try:
            await context.bot.send_message(
                chat_id=reply_data['user_id'],
                text=f"📨 رد من الإدارة:\n\n{reply_data['message']}"
            )
            await query.edit_message_text("✅ تم إرسال الرد")
            
            await log_admin_action(
                query.from_user.id, 
                "admin_reply", 
                reply_data['user_id']
            )
            
        except Exception as e:
            logger.error(f"Error replying to {reply_data['user_id']}: {e}")
            await query.edit_message_text("❌ فشل إرسال الرد")
    else:
        await query.edit_message_text("❌ تم إلغاء إرسال الرد")
    
    return ConversationHandler.END

async def import_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Import users from Excel with confirmation"""
    if not await is_admin(update.message.from_user.id):
        await update.message.reply_text("❌ Admin only command")
        return

    if not update.message.document:
        await update.message.reply_text("❌ Please send an Excel (.xlsx) file")
        return

    try:
        # Download file
        file = await context.bot.get_file(update.message.document.file_id)
        filename = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        await file.download_to_drive(filename)
        
        # Read Excel to show preview
        df = pd.read_excel(filename)
        preview = df.head(3).to_string(index=False)
        
        context.user_data['import_file'] = filename
        
        keyboard = [
            [InlineKeyboardButton("✅ تأكيد الاستيراد", callback_data="confirm_import")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_import")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ هل أنت متأكد من أنك تريد استيراد هذا الملف؟\n\n"
            f"معاينة البيانات (أول 3 صفوف):\n{preview}",
            reply_markup=reply_markup
        )
        return "confirm_import"

    except Exception as e:
        logger.error(f"Error reading import file: {str(e)}", exc_info=True)
        await update.message.reply_text(f"❌ خطأ في قراءة الملف: {str(e)}")
        if os.path.exists(filename):
            os.remove(filename)
        return ConversationHandler.END

async def confirm_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute import"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    if query.data == "confirm_import":
        filename = context.user_data.get('import_file')
        
        try:
            await query.edit_message_text("🔄 Processing your file...")
            
            # Read Excel with enhanced validation
            df = pd.read_excel(filename)
            required_columns = ['username', 'name', 'telegram_id']
            
            # Validate columns
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                await query.edit_message_text(f"❌ Missing columns: {', '.join(missing)}")
                os.remove(filename)
                return
                
            success = 0
            errors = []
            user_ids = []
            
            async with aiosqlite.connect(DATABASE) as db:
                for index, row in df.iterrows():
                    try:
                        # Generate values with defaults
                        values = {
                            'username': str(row.get('username', '')).strip(),
                            'name': str(row.get('name', '')).strip(),
                            'age': int(row.get('age', 0)),
                            'bio': str(row.get('bio', '')).strip(),
                            'type': str(row.get('type', '')).strip(),
                            'location': str(row.get('location', '')).strip(),
                            'photo': str(row.get('photo', '')).strip(),
                            'country': str(row.get('country', '')).strip(),
                            'city': str(row.get('city', '')).strip(),
                            'telegram_id': int(row['telegram_id']),
                            'banned': int(row.get('banned', 0)),
                            'frozen': int(row.get('frozen', 0)),
                            'admin': int(row.get('admin', 0))
                        }
                        
                        # Validate required fields
                        if not values['username'] or not values['name'] or not values['telegram_id']:
                            raise ValueError("Missing required field")
                        
                        await db.execute(
                            """INSERT OR REPLACE INTO users 
                            (username, name, age, bio, type, 
                             location, photo, country, city,
                             telegram_id, banned, frozen, admin)
                            VALUES (:username, :name, :age, :bio, :type, 
                                    :location, :photo, :country, :city,
                                    :telegram_id, :banned, :frozen, :admin)""",
                            values
                        )
                        success += 1
                        user_ids.append(values['telegram_id'])
                    except Exception as e:
                        errors.append(f"Row {index+2}: {str(e)}")
                
                await db.commit()
            
            # Generate detailed report
            report = [
                f"📊 Import Report",
                f"✅ Success: {success}",
                f"❌ Errors: {len(errors)}",
                f"📥 Total in file: {len(df)}"
            ]
            
            # Add verification count
            async with aiosqlite.connect(DATABASE) as db:
                cursor = await db.execute(
                    f"SELECT COUNT(*) FROM users WHERE telegram_id IN ({','.join(map(str, user_ids))})"
                )
                verified_count = (await cursor.fetchone())[0]
                report.append(f"🔍 Verified in DB: {verified_count}")
            
            # Add error samples if any
            if errors:
                report.append("\n⚠ First 3 errors:")
                report.extend(errors[:3])
                if len(errors) > 3:
                    report.append(f"...plus {len(errors)-3} more")
            
            # Send final report
            await query.edit_message_text("\n".join(report))
            
            # Offer to export verification
            keyboard = [
                [InlineKeyboardButton("📤 Export Current Database", callback_data="export_verify")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Would you like to verify the current database state?",
                reply_markup=reply_markup
            )
            
            await log_admin_action(
                query.from_user.id, 
                "import_users", 
                details=f"Imported {success} users"
            )
            
            os.remove(filename)

        except Exception as e:
            logger.error(f"Import failed: {str(e)}", exc_info=True)
            await query.edit_message_text(f"❌ Critical error: {str(e)}")
            if os.path.exists(filename):
                os.remove(filename)
    else:
        filename = context.user_data.get('import_file')
        if os.path.exists(filename):
            os.remove(filename)
        await query.edit_message_text("❌ تم إلغاء عملية الاستيراد")
    
    return ConversationHandler.END

async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export all users to Excel with confirmation"""
    if not await is_admin(update.message.from_user.id):
        await update.message.reply_text("❌ Admin only command")
        return

    keyboard = [
        [InlineKeyboardButton("✅ تأكيد التصدير", callback_data="confirm_export")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_export")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ هل أنت متأكد من أنك تريد تصدير قاعدة بيانات المستخدمين؟",
        reply_markup=reply_markup
    )
    return "confirm_export"

async def confirm_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute export"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    if query.data == "confirm_export":
        try:
            await query.edit_message_text("⏳ Preparing export...")
            
            async with aiosqlite.connect(DATABASE) as db:
                cursor = await db.execute("SELECT * FROM users")
                users = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                output = BytesIO()
                df = pd.DataFrame(users, columns=columns)
                df.to_excel(output, index=False)
                output.seek(0)
                
                await context.bot.send_document(
                    chat_id=query.from_user.id,
                    document=output,
                    filename=f"users_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    caption="📊 Users database export"
                )
                
            await query.edit_message_text("✅ Export completed successfully")
            
            await log_admin_action(query.from_user.id, "export_users")
            
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            await query.edit_message_text("❌ Failed to export user data")
    else:
        await query.edit_message_text("❌ تم إلغاء عملية التصدير")
    
    return ConversationHandler.END

async def export_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export current database for verification"""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text("⏳ Preparing database export...")
        
        async with aiosqlite.connect(DATABASE) as db:
            # Get all users
            cursor = await db.execute("SELECT * FROM users")
            users = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            # Create Excel in memory
            output = BytesIO()
            df = pd.DataFrame(users, columns=columns)
            df.to_excel(output, index=False)
            output.seek(0)
            
            # Send file
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=output,
                filename=f"database_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
                caption="📤 Full database export"
            )
            
        await query.edit_message_text("✅ Database exported successfully")
        
        await log_admin_action(query.from_user.id, "export_verification")
        
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        await query.edit_message_text("❌ Failed to export database")

async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a database backup"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    try:
        await query.edit_message_text("⏳ Creating database backup...")
        backup_file = await backup_database()
        
        if backup_file:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=open(backup_file, 'rb'),
                filename=os.path.basename(backup_file),
                caption="💾 Database backup"
            )
            await query.edit_message_text("✅ Backup created successfully")
            await log_admin_action(query.from_user.id, "create_backup")
        else:
            await query.edit_message_text("❌ Failed to create backup")
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        await query.edit_message_text("❌ Failed to create backup")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user with confirmation"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    user_id = int(query.data.replace("ban_", ""))
    
    context.user_data['ban_user'] = user_id
    
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد الحظر", callback_data=f"confirm_ban_{user_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_ban_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ هل أنت متأكد من أنك تريد حظر المستخدم {user_id}؟",
        reply_markup=reply_markup
    )

async def confirm_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute ban"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    if query.data.startswith("confirm_ban_"):
        user_id = int(query.data.replace("confirm_ban_", ""))
        
        try:
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute(
                    "UPDATE users SET banned = 1 WHERE telegram_id = ?",
                    (user_id,)
                )
                await db.commit()
            
            await query.edit_message_text(f"✅ User {user_id} banned")
            
            await log_admin_action(query.from_user.id, "ban_user", user_id)
            
            # Notify the banned user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ تم حظر حسابك من استخدام البوت. الرجاء التواصل مع الإدارة إذا كان هناك خطأ."
                )
            except Exception as e:
                logger.error(f"Error notifying banned user: {e}")
            
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
            await query.edit_message_text(f"❌ Failed to ban user {user_id}")
    else:
        user_id = int(query.data.replace("cancel_ban_", ""))
        await query.edit_message_text(f"❌ تم إلغاء حظر المستخدم {user_id}")

async def freeze_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Freeze a user account with confirmation"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    user_id = int(query.data.replace("freeze_", ""))
    
    context.user_data['freeze_user'] = user_id
    
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد التجميد", callback_data=f"confirm_freeze_{user_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_freeze_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ هل أنت متأكد من أنك تريد تجميد حساب المستخدم {user_id}؟",
        reply_markup=reply_markup
    )

async def confirm_freeze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute freeze"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    if query.data.startswith("confirm_freeze_"):
        user_id = int(query.data.replace("confirm_freeze_", ""))
        
        try:
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute(
                    "UPDATE users SET frozen = 1 WHERE telegram_id = ?",
                    (user_id,)
                )
                await db.commit()
            
            await query.edit_message_text(f"✅ User {user_id} frozen")
            
            await log_admin_action(query.from_user.id, "freeze_user", user_id)
            
            # Notify the frozen user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❄️ تم تجميد حسابك مؤقتًا. الرجاء التواصل مع الإدارة إذا كان هناك خطأ."
                )
            except Exception as e:
                logger.error(f"Error notifying frozen user: {e}")
            
        except Exception as e:
            logger.error(f"Error freezing user {user_id}: {e}")
            await query.edit_message_text(f"❌ Failed to freeze user {user_id}")
    else:
        user_id = int(query.data.replace("cancel_freeze_", ""))
        await query.edit_message_text(f"❌ تم إلغاء تجميد المستخدم {user_id}")

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote a user to admin with confirmation"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    user_id = int(query.data.replace("promote_", ""))
    
    context.user_data['promote_user'] = user_id
    
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد الترقية", callback_data=f"confirm_promote_{user_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_promote_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ هل أنت متأكد من أنك تريد ترقية المستخدم {user_id} إلى مدير؟",
        reply_markup=reply_markup
    )

async def confirm_promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute promotion"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    if query.data.startswith("confirm_promote_"):
        user_id = int(query.data.replace("confirm_promote_", ""))
        
        try:
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute(
                    "UPDATE users SET admin = 1 WHERE telegram_id = ?",
                    (user_id,)
                )
                await db.commit()
            
            await query.edit_message_text(f"✅ User {user_id} promoted to admin")
            
            await log_admin_action(query.from_user.id, "promote_user", user_id)
            
            # Notify the promoted user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="👑 تم ترقيتك إلى مدير في البوت. يمكنك الآن استخدام لوحة التحكم الإدارية."
                )
            except Exception as e:
                logger.error(f"Error notifying promoted user: {e}")
            
        except Exception as e:
            logger.error(f"Error promoting user {user_id}: {e}")
            await query.edit_message_text(f"❌ Failed to promote user {user_id}")
    else:
        user_id = int(query.data.replace("cancel_promote_", ""))
        await query.edit_message_text(f"❌ تم إلغاء ترقية المستخدم {user_id}")

async def admin_profile_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin actions for a profile"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    user_id = int(query.data.replace("admin_profile_", ""))
    
    keyboard = [
        [
            InlineKeyboardButton("⛔ حظر", callback_data=f"ban_{user_id}"),
            InlineKeyboardButton("❄️ تجميد", callback_data=f"freeze_{user_id}")
        ],
        [
            InlineKeyboardButton("👑 ترقية", callback_data=f"promote_{user_id}"),
            InlineKeyboardButton("↩️ رجوع", callback_data="admin_users")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🛠 إجراءات الإدارة للمستخدم {user_id}:",
        reply_markup=reply_markup
    )

async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """No operation callback for buttons that shouldn't do anything"""
    query = update.callback_query
    await query.answer()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and send user-friendly message"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى لاحقًا."
        )

async def set_bot_commands(application):
    """Set bot commands for menu"""
    commands = [
        ("start", "بدء استخدام البوت"),
        ("search", "البحث عن أشخاص قريبين"),
        ("feedback", "إرسال ملاحظات"),
        ("report", "الإبلاغ عن مستخدم"),
        ("help", "مساعدة")
    ]
    
    await application.bot.set_my_commands(commands)

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

    # Admin handlers
    admin_view_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_view_user, pattern="^admin_view_user$")],
        states={
            "view_user": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_view_user)]
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )
    
    broadcast_handler = ConversationHandler(
        entry_points=[CommandHandler('broadcast', broadcast)],
        states={
            "broadcast": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast)],
            "confirm_broadcast": [CallbackQueryHandler(confirm_broadcast)]
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )
    
    extract_handler = ConversationHandler(
        entry_points=[CommandHandler('extract', extract_group_members)],
        states={
            "confirm_extract": [CallbackQueryHandler(confirm_extract)]
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )
    
    reply_handler = ConversationHandler(
        entry_points=[CommandHandler('reply', admin_reply)],
        states={
            "confirm_reply": [CallbackQueryHandler(confirm_reply)]
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )
    
    import_handler = ConversationHandler(
        entry_points=[CommandHandler('import', import_users)],
        states={
            "confirm_import": [CallbackQueryHandler(confirm_import)]
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )
    
    export_handler = ConversationHandler(
        entry_points=[CommandHandler('export', export_users)],
        states={
            "confirm_export": [CallbackQueryHandler(confirm_export)]
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
    )

    # Add all handlers
    application.add_handlers([
        conv_handler,
        feedback_handler,
        report_handler,
        admin_view_handler,
        broadcast_handler,
        extract_handler,
        reply_handler,
        import_handler,
        export_handler,
        CommandHandler('search', show_nearby_profiles),
        CommandHandler('admin', admin_panel),
        CallbackQueryHandler(admin_stats, pattern="^admin_stats$"),
        CallbackQueryHandler(admin_users, pattern="^admin_users$"),
        CallbackQueryHandler(admin_list_users, pattern=r"^admin_list_users_\d+$"),
        CallbackQueryHandler(admin_panel, pattern="^admin_panel$"),
        CallbackQueryHandler(admin_profile_actions, pattern="^admin_profile_"),
        CallbackQueryHandler(ban_user, pattern="^ban_"),
        CallbackQueryHandler(confirm_ban, pattern="^confirm_ban_"),
        CallbackQueryHandler(confirm_ban, pattern="^cancel_ban_"),
        CallbackQueryHandler(freeze_user, pattern="^freeze_"),
        CallbackQueryHandler(confirm_freeze, pattern="^confirm_freeze_"),
        CallbackQueryHandler(confirm_freeze, pattern="^cancel_freeze_"),
        CallbackQueryHandler(promote_user, pattern="^promote_"),
        CallbackQueryHandler(confirm_promote, pattern="^confirm_promote_"),
        CallbackQueryHandler(confirm_promote, pattern="^cancel_promote_"),
        CallbackQueryHandler(export_verification, pattern="^export_verify$"),
        CallbackQueryHandler(admin_backup, pattern="^admin_backup$"),
        CallbackQueryHandler(noop, pattern="^noop$")
    ])

    # Add error handler
    application.add_error_handler(error_handler)

    # Set bot commands
    await set_bot_commands(application)
    
    # Start the bot
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
