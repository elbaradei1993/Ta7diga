import logging
import asyncio
import nest_asyncio
import aiosqlite
from geopy.distance import geodesic
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak")  # Replace with your actual token
DATABASE = os.getenv("DATABASE", "users.db")
ADMIN_ID = 1796978458  # Replace with your Telegram user ID
BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# List of countries and cities
COUNTRIES = {
    "السودان": ["الخرطوم", "أم درمان", "بحري", "بورتسودان"],
    "مصر": ["القاهرة", "الإسكندرية"],
    "السعودية": ["الرياض", "جدة"]
}

# Conversation states
(
    USERNAME, NAME, AGE, BIO, TYPE, 
    COUNTRY, CITY, LOCATION, PHOTO,
    FEEDBACK, REPORT,
    BROADCAST_MESSAGE,
    BAN_USER, FREEZE_USER, PROMOTE_USER,
    ADMIN_BACK
) = range(16)

async def init_db():
    """Initialize database with all tables"""
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Users table
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
            
            # Feedback table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )""")
            
            # Reports table
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
            
            # Admin logs
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
            
            await db.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def is_admin(user_id: int) -> bool:
    """Check if user has admin privileges"""
    if user_id == ADMIN_ID:
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
        logger.error(f"Admin check failed for {user_id}: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT banned, frozen FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            user_status = await cursor.fetchone()
            
            if user_status:
                if user_status[0]:  # banned
                    await update.message.reply_text("❌ حسابك محظور.")
                    return ConversationHandler.END
                elif user_status[1]:  # frozen
                    await update.message.reply_text("❄️ حسابك مجمد مؤقتًا.")
                    return ConversationHandler.END
                else:
                    await update.message.reply_text("مرحبًا بك مجددًا! استخدم /search للبحث.")
                    return ConversationHandler.END
    except Exception as e:
        logger.error(f"Start command error for {user.id}: {e}")
    
    # Start registration
    await show_terms(update, context)
    return USERNAME

async def show_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display terms and conditions"""
    terms = """
    📜 شروط وأحكام الاستخدام:
    1. يجب أن تكون +18 سنة
    2. المحتوى المسيء ممنوع
    3. احترام خصوصية الآخرين
    """
    keyboard = [
        [InlineKeyboardButton("✅ أوافق", callback_data="agree_terms")],
        [InlineKeyboardButton("❌ لا أوافق", callback_data="decline_terms")]
    ]
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            terms, 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            terms, 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return USERNAME

async def handle_terms_acceptance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle terms acceptance"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "agree_terms":
        await query.edit_message_text("الآن، أرسل اسم المستخدم الخاص بك:")
        return USERNAME
    else:
        await query.edit_message_text("يجب الموافقة على الشروط لاستخدام البوت.")
        return ConversationHandler.END

async def set_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set username during registration"""
    if update.callback_query:
        return USERNAME
    
    username = update.message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
        await update.message.reply_text("اسم المستخدم غير صالح (5-32 حرف، أحرف وأرقام فقط)")
        return USERNAME
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (username,)
            )
            if await cursor.fetchone():
                await update.message.reply_text("اسم المستخدم موجود مسبقًا، اختر اسمًا آخر")
                return USERNAME
    except Exception as e:
        logger.error(f"Username check failed: {e}")
        await update.message.reply_text("حدث خطأ، حاول لاحقًا")
        return ConversationHandler.END
    
    context.user_data['username'] = username
    await update.message.reply_text("الآن، أرسل اسمك الكامل:")
    return NAME

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set full name during registration"""
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text("الاسم يجب أن يكون بين 2-50 حرفًا")
        return NAME
    
    context.user_data['name'] = name
    await update.message.reply_text("أرسل عمرك:")
    return AGE

async def set_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set age during registration"""
    try:
        age = int(update.message.text)
        if age < 18 or age > 100:
            await update.message.reply_text("العمر يجب أن يكون بين 18-100")
            return AGE
    except ValueError:
        await update.message.reply_text("الرجاء إدخال رقم صحيح")
        return AGE
    
    context.user_data['age'] = age
    await update.message.reply_text("أرسل نبذة عنك (10-500 حرف):")
    return BIO

async def set_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set bio during registration"""
    bio = update.message.text.strip()
    if len(bio) < 10 or len(bio) > 500:
        await update.message.reply_text("النبذة يجب أن تكون بين 10-500 حرف")
        return BIO
    
    context.user_data['bio'] = bio
    
    keyboard = [
        [InlineKeyboardButton("👨 رجل", callback_data="male")],
        [InlineKeyboardButton("👩 امرأة", callback_data="female")]
    ]
    await update.message.reply_text(
        "اختر جنسك:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TYPE

async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set gender type during registration"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['type'] = query.data
    
    keyboard = [
        [InlineKeyboardButton(country, callback_data=f"country_{country}")]
        for country in COUNTRIES.keys()
    ]
    await query.edit_message_text(
        "اختر بلدك:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return COUNTRY

async def set_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set country during registration"""
    query = update.callback_query
    await query.answer()
    
    country = query.data.replace("country_", "")
    context.user_data['country'] = country
    
    cities = COUNTRIES.get(country, [])
    keyboard = [
        [InlineKeyboardButton(city, callback_data=f"city_{city}")]
        for city in cities
    ]
    await query.edit_message_text(
        "اختر مدينتك:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CITY

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set city during registration"""
    query = update.callback_query
    await query.answer()
    
    city = query.data.replace("city_", "")
    context.user_data['city'] = city
    
    await query.edit_message_text("أرسل موقعك الجغرافي:")
    return LOCATION

async def set_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set location during registration"""
    location = update.message.location
    context.user_data['location'] = f"{location.latitude},{location.longitude}"
    
    await update.message.reply_text("أرسل صورتك:")
    return PHOTO

async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set profile photo during registration"""
    photo = update.message.photo[-1].file_id
    context.user_data['photo'] = photo
    
    # Complete registration
    user = update.effective_user
    user_data = context.user_data
    
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
        
        await update.message.reply_text("🎉 تم التسجيل بنجاح! استخدم /search للبحث عن أشخاص قريبين.")
        
        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 مستخدم جديد:\nالاسم: {user_data.get('name')}\nالعمر: {user_data.get('age')}\nالمدينة: {user_data.get('city')}"
        )
    except Exception as e:
        logger.error(f"Registration failed for {user.id}: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء التسجيل.")
    
    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel registration process"""
    await update.message.reply_text("تم إلغاء التسجيل.")
    return ConversationHandler.END

async def show_nearby_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show nearby profiles to user"""
    user = update.effective_user
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Check if user exists and is not banned/frozen
            cursor = await db.execute(
                "SELECT location, banned, frozen FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            user_data = await cursor.fetchone()
            
            if not user_data:
                await update.message.reply_text("❌ يجب التسجيل أولاً باستخدام /start")
                return
            if user_data[1]:  # banned
                await update.message.reply_text("❌ حسابك محظور.")
                return
            if user_data[2]:  # frozen
                await update.message.reply_text("❄️ حسابك مجمد مؤقتًا.")
                return
            if not user_data[0]:  # no location
                await update.message.reply_text("❌ يجب مشاركة موقعك الجغرافي أولاً")
                return
            
            lat, lon = map(float, user_data[0].split(','))
            
            # Get nearby users (within 50km)
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id != ? AND banned = 0 AND frozen = 0",
                (user.id,)
            )
            users = await cursor.fetchall()
            
            nearby_users = []
            for u in users:
                if not u[6]:  # no location
                    continue
                
                u_lat, u_lon = map(float, u[6].split(','))
                distance = geodesic((lat, lon), (u_lat, u_lon)).km
                
                if distance <= 50:
                    nearby_users.append((u, distance))
            
            if not nearby_users:
                await update.message.reply_text("لا يوجد أشخاص قريبين منك الآن.")
                return
            
            # Show top 10 nearest
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
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=caption,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🚀 إرسال رسالة", url=f"https://t.me/{u[1]}")]
                        ])
                    )
                
    except Exception as e:
        logger.error(f"Error showing nearby profiles: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء البحث.")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start feedback conversation"""
    await update.message.reply_text(
        "📝 أرسل ملاحظاتك أو اقتراحاتك:\n"
        "يمكنك إرسال /cancel للإلغاء"
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
        
        await update.message.reply_text("شكرًا لك على ملاحظاتك!")
        
        # Notify admin
        username = f"@{user.username}" if user.username else f"user_{user.id}"
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📝 ملاحظات جديدة من {username}:\n\n{feedback_text}"
        )
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حفظ الملاحظات.")
    
    return ConversationHandler.END

async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start report conversation"""
    await update.message.reply_text(
        "⚠️ أرسل تقريرك عن المستخدم (مع ذكر @username):\n"
        "يمكنك إرسال /cancel للإلغاء"
    )
    return REPORT

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user report"""
    report_text = update.message.text
    user = update.effective_user
    
    # Extract username
    username_match = re.search(r'@([a-zA-Z0-9_]{5,32})', report_text)
    if not username_match:
        await update.message.reply_text("❌ يجب ذكر اسم المستخدم (مثال: @username)")
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
                await update.message.reply_text("❌ لم يتم العثور على المستخدم")
                return REPORT
            
            await db.execute(
                "INSERT INTO reports (user_id, reported_user_id, message) VALUES (?, ?, ?)",
                (user.id, reported_user[0], report_text)
            )
            await db.commit()
        
        await update.message.reply_text("شكرًا لك على التقرير، سنقوم بمراجعته.")
        
        # Notify admin
        reporter = f"@{user.username}" if user.username else f"user_{user.id}"
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ تقرير جديد من {reporter}:\nالمبلغ عنه: @{username}\nالتقرير:\n{report_text}"
        )
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حفظ التقرير.")
    
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel"""
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👤 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📢 بث رسالة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📤 تصدير البيانات", callback_data="admin_export")]
    ]
    
    await update.message.reply_text(
        "🛠 لوحة التحكم:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics"""
    query = update.callback_query
    await query.answer()
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Get counts
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
            banned_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE frozen = 1")
            frozen_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM reports WHERE timestamp > datetime('now', '-7 days')")
            recent_reports = (await cursor.fetchone())[0]
            
            stats = (
                f"📊 الإحصائيات:\n\n"
                f"👥 إجمالي المستخدمين: {total_users}\n"
                f"⛔ محظورين: {banned_users}\n"
                f"❄️ مجمدين: {frozen_users}\n"
                f"⚠️ تقارير هذا الأسبوع: {recent_reports}"
            )
            
            await query.edit_message_text(
                stats,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
                ])
            )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        await query.edit_message_text("❌ فشل جلب الإحصائيات.")

async def handle_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user management options"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("⛔ حظر مستخدم", callback_data="admin_ban")],
        [InlineKeyboardButton("❄️ تجميد مستخدم", callback_data="admin_freeze")],
        [InlineKeyboardButton("👑 رفع مسؤول", callback_data="admin_promote")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        "👤 إدارة المستخدمين:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast message process"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 أرسل الرسالة للبث:\n"
        "يمكنك إرسال /cancel للإلغاء",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ])
    )
    return BROADCAST_MESSAGE

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to all users"""
    user = update.effective_user
    if not await is_admin(user.id):
        return
    
    message = update.message.text
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT telegram_id FROM users WHERE banned = 0")
            users = await cursor.fetchall()
        
        success = 0
        for user_id, in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 إشعار من الإدارة:\n\n{message}"
                )
                success += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"Broadcast failed for {user_id}: {e}")
        
        await update.message.reply_text(f"✅ تم الإرسال لـ {success} مستخدم")
        
        # Log the broadcast
        await log_admin_action(
            user.id,
            "broadcast",
            details=f"Sent to {success} users"
        )
    
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        await update.message.reply_text("❌ فشل البث")
    
    return ConversationHandler.END

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to admin panel"""
    query = update.callback_query
    if query:
        await query.answer()
        await admin_panel(update, context)
    return ConversationHandler.END

async def log_admin_action(admin_id: int, action: str, target_id: int = None, details: str = None):
    """Log admin actions to database"""
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (?, ?, ?, ?)",
                (admin_id, action, target_id, details)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export user data to Excel"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT * FROM users")
            users = await cursor.fetchall()
            
            # Create DataFrame
            df = pd.DataFrame(users, columns=[
                'id', 'username', 'name', 'age', 'bio', 'type', 
                'location', 'photo', 'country', 'city', 'telegram_id',
                'banned', 'frozen', 'admin', 'joined_at'
            ])
            
            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Users', index=False)
            
            output.seek(0)
            
            # Send file
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=output,
                filename=f"users_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
                caption="📤 تصدير بيانات المستخدمين"
            )
            
    except Exception as e:
        logger.error(f"Export failed: {e}")
        await update.message.reply_text("❌ فشل تصدير البيانات")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    if not context.args:
        await update.message.reply_text("الاستخدام: /broadcast <الرسالة>")
        return
    
    message = ' '.join(context.args)
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT telegram_id FROM users WHERE banned = 0")
            users = await cursor.fetchall()
        
        success = 0
        for user_id, in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 إشعار من الإدارة:\n\n{message}"
                )
                success += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"Broadcast failed for {user_id}: {e}")
        
        await update.message.reply_text(f"✅ تم الإرسال لـ {success} مستخدم")
        
        # Log the broadcast
        await log_admin_action(
            update.effective_user.id,
            "broadcast",
            details=f"Sent to {success} users"
        )
    
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        await update.message.reply_text("❌ فشل البث")

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a specific user"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("الاستخدام: /reply <user_id> <الرسالة>")
        return
    
    user_id = context.args[0]
    message = ' '.join(context.args[1:])
    
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"📬 رد من الإدارة:\n\n{message}"
        )
        await update.message.reply_text("✅ تم إرسال الرد")
        
        # Log the action
        await log_admin_action(
            update.effective_user.id,
            "reply",
            target_id=int(user_id),
            details=message
        )
    except Exception as e:
        logger.error(f"Reply failed: {e}")
        await update.message.reply_text("❌ فشل إرسال الرد")

async def import_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Import user data from Excel"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    if not update.message.document:
        await update.message.reply_text("الرجاء إرفاق ملف Excel للاستيراد")
        return
    
    try:
        # Download the file
        file = await context.bot.get_file(update.message.document.file_id)
        file_path = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        await file.download_to_drive(file_path)
        
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Ensure required columns exist
        required_columns = ['username', 'name', 'age', 'bio', 'type', 
                          'location', 'photo', 'country', 'city', 'telegram_id',
                          'banned', 'frozen', 'admin']
        
        if not all(col in df.columns for col in required_columns):
            await update.message.reply_text("❌ ملف Excel لا يحتوي على الأعمدة المطلوبة.")
            return
        
        # Process each row
        async with aiosqlite.connect(DATABASE) as db:
            for _, row in df.iterrows():
                # Convert NaN values to None
                row = row.where(pd.notnull(row), None)
                
                await db.execute(
                    """INSERT OR REPLACE INTO users (
                        username, name, age, bio, type,
                        location, photo, country, city, telegram_id,
                        banned, frozen, admin, joined_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT joined_at FROM users WHERE telegram_id = ?), datetime('now')))""",
                    (
                        row['username'], row['name'], row['age'], row['bio'],
                        row['type'], row['location'], row['photo'], row['country'],
                        row['city'], row['telegram_id'], row['banned'] or 0,
                        row['frozen'] or 0, row['admin'] or 0, row['telegram_id']
                    )
                )
            await db.commit()
        
        await update.message.reply_text(f"✅ تم استيراد {len(df)} مستخدم بنجاح")
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        await update.message.reply_text(f"❌ فشل استيراد البيانات: {str(e)}")

async def extract_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract the entire database"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    try:
        backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        async with aiosqlite.connect(DATABASE) as src:
            async with aiosqlite.connect(backup_file) as dst:
                await src.backup(dst)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(backup_file, 'rb'),
            caption="💾 نسخة احتياطية من قاعدة البيانات"
        )
        
    except Exception as e:
        logger.error(f"Extract failed: {e}")
        await update.message.reply_text("❌ فشل استخراج قاعدة البيانات")

async def extract_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract group members and format for database"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    if not context.args:
        await update.message.reply_text("الرجاء إدخال معرف المجموعة (مثال: /extract_group -100123456789)")
        return
    
    group_id = context.args[0]
    
    try:
        members = []
        async for member in context.bot.get_chat_members(group_id):
            user = member.user
            
            # Skip bots
            if user.is_bot:
                continue
                
            members.append({
                'username': user.username or f"user_{user.id}",
                'name': user.full_name,
                'age': 25,  # Default age
                'bio': "مستخدم مستورد من مجموعة",
                'type': "male",  # Default type
                'location': None,
                'photo': None,
                'country': "غير محدد",
                'city': "غير محدد",
                'telegram_id': user.id,
                'banned': 0,
                'frozen': 0,
                'admin': 0
            })
        
        if not members:
            await update.message.reply_text("❌ لم يتم العثور على أعضاء في المجموعة")
            return
        
        # Create DataFrame
        df = pd.DataFrame(members)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Group Members', index=False)
        
        output.seek(0)
        
        # Send file
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=output,
            filename=f"group_members_{datetime.now().strftime('%Y%m%d')}.xlsx",
            caption=f"📊 أعضاء المجموعة ({len(members)} مستخدم)"
        )
        
    except Exception as e:
        logger.error(f"Extract failed: {e}")
        await update.message.reply_text(f"❌ فشل استخراج الأعضاء: {str(e)}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors globally"""
    logger.error("Exception while handling update:", exc_info=context.error)
    
    try:
        if update and hasattr(update, 'effective_chat'):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ حدث خطأ غير متوقع. تم إبلاغ الإدارة."
            )
    except Exception as e:
        logger.error("Error while notifying user:", exc_info=e)
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ خطأ في البوت:\n\n{context.error}"
        )
    except Exception as e:
        logger.error("Error while notifying admin:", exc_info=e)

async def main():
    """Main application entry point"""
    await init_db()
    
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .build()

    # Registration handler
    registration = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_username),
                CallbackQueryHandler(handle_terms_acceptance)
            ],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_age)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_bio)],
            TYPE: [CallbackQueryHandler(set_type)],
            COUNTRY: [CallbackQueryHandler(set_country)],
            CITY: [CallbackQueryHandler(set_city)],
            LOCATION: [MessageHandler(filters.LOCATION, set_location)],
            PHOTO: [MessageHandler(filters.PHOTO, set_photo)]
        },
        fallbacks=[CommandHandler('cancel', cancel_registration)],
    )

    # Feedback handler
    feedback_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', feedback)],
        states={
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)]
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)]
    )

    # Report handler
    report_handler = ConversationHandler(
        entry_points=[CommandHandler('report', report_user)],
        states={
            REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report)]
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)]
    )

    # Admin broadcast handler
    broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern="^admin_broadcast$")],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)]
        },
        fallbacks=[CommandHandler('cancel', admin_back)]
    )

    # Add all handlers
    application.add_handler(registration)
    application.add_handler(CommandHandler('search', show_nearby_profiles))
    application.add_handler(feedback_handler)
    application.add_handler(report_handler)
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CallbackQueryHandler(handle_admin_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(handle_admin_users, pattern="^admin_users$"))
    application.add_handler(broadcast_handler)
    application.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    
    # Add the new admin command handlers
    application.add_handler(CommandHandler('export', export_data))
    application.add_handler(CommandHandler('broadcast', broadcast_message))
    application.add_handler(CommandHandler('reply', reply_to_user))
    application.add_handler(CommandHandler('import', import_data))
    application.add_handler(CommandHandler('extract', extract_database))
    application.add_handler(CommandHandler('extract_group', extract_group_members))
    
    # Error handler
    application.add_error_handler(error_handler)

    # Start the bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot is running and polling...")
    
    # Keep the application running
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
