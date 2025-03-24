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
                    admin INTEGER DEFAULT 0,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            await db.execute(
                """CREATE TABLE IF NOT EXISTS group_members (
                    user_id INTEGER,
                    group_id INTEGER,
                    group_title TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, group_id)
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
            await db.execute(
                """CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    target_id INTEGER,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            await db.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
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
    username = update.message.text
    context.user_data['username'] = username
    
    await update.message.reply_text(
        "تم حفظ اسم المستخدم.\n\n"
        "الرجاء إرسال اسمك الكامل:"
    )
    return NAME

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store name and ask for age"""
    name = update.message.text
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
            await update.message.reply_text("الرجاء إدخال عمر بين 18 و 100")
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
    bio = update.message.text
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
                        caption=caption
                    )
                except telegram.error.BadRequest:
                    await update.message.reply_text(caption)
                
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
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "INSERT INTO reports (user_id, message) VALUES (?, ?)",
                (user.id, report_text)
            )
            await db.commit()
            
        await update.message.reply_text(
            "شكرًا لك على التقرير! سنقوم بمراجعته قريبًا."
        )
        
        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ تقرير جديد من @{user.username}:\n\n{report_text}"
        )
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حفظ تقريرك. الرجاء المحاولة لاحقًا.")
    
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel with working buttons"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👤 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📤 تصدير البيانات", callback_data="admin_export")],
        [InlineKeyboardButton("📥 استيراد البيانات", callback_data="admin_import")],
        [InlineKeyboardButton("📢 بث رسالة", callback_data="admin_broadcast")]
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
    
    if query.from_user.id != ADMIN_ID:
        return
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
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
    
    if query.from_user.id != ADMIN_ID:
        return
    
    keyboard = [
        [InlineKeyboardButton("🔍 عرض مستخدم", callback_data="admin_view_user")],
        [InlineKeyboardButton("⛔ حظر مستخدم", callback_data="admin_ban_user")],
        [InlineKeyboardButton("❄️ تجميد مستخدم", callback_data="admin_freeze_user")],
        [InlineKeyboardButton("👑 ترقية مستخدم", callback_data="admin_promote_user")],
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
    
    if query.from_user.id != ADMIN_ID:
        return
    
    await query.edit_message_text(
        "الرجاء إرسال معرف المستخدم (ID) أو اسم المستخدم (@username):"
    )
    return "view_user"

async def handle_view_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle viewing user details"""
    if update.message.from_user.id != ADMIN_ID:
        return
    
    user_input = update.message.text.strip()
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            if user_input.startswith('@'):
                cursor = await db.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (user_input[1:],)
            else:
                try:
                    user_id = int(user_input)
                    cursor = await db.execute(
                        "SELECT * FROM users WHERE telegram_id = ? OR id = ?",
                        (user_id, user_id))
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
                    chat_id=ADMIN_ID,
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

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast conversation with confirmation"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command")
        return
    
    await update.message.reply_text(
        "📢 الرجاء إرسال الرسالة التي تريد بثها لجميع المستخدمين:\n\n"
        "يمكنك إرسال /cancel لإلغاء الأمر."
    )
    return "broadcast"

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message with confirmation"""
    if update.message.from_user.id != ADMIN_ID:
        return
    
    message = update.message.text
    if not message:
        await update.message.reply_text("❌ الرسالة فارغة")
        return "broadcast"
    
    context.user_data['broadcast_message'] = message
    
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد البث", callback_data="confirm_broadcast")],
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
    
    if query.from_user.id != ADMIN_ID:
        return
    
    if query.data == "confirm_broadcast":
        message = context.user_data.get('broadcast_message')
        
        try:
            async with aiosqlite.connect(DATABASE) as db:
                cursor = await db.execute("SELECT telegram_id FROM users WHERE banned = 0 AND frozen = 0")
                users = await cursor.fetchall()
                
            success = 0
            failed = 0
            
            await query.edit_message_text("⏳ جاري إرسال الرسالة...")
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user[0],
                        text=message
                    )
                    success += 1
                except Exception as e:
                    logger.error(f"Error sending to {user[0]}: {e}")
                    failed += 1
            
            await query.edit_message_text(
                f"✅ تم إرسال الرسالة إلى {success} مستخدم\n"
                f"❌ فشل الإرسال إلى {failed} مستخدم"
            )
            
            await log_admin_action(query.from_user.id, "broadcast", details=f"Sent to {success}, failed {failed}")
            
        except Exception as e:
            logger.error(f"Error broadcasting: {e}")
            await query.edit_message_text("❌ حدث خطأ أثناء البث. الرجاء المحاولة لاحقًا.")
    else:
        await query.edit_message_text("❌ تم إلغاء عملية البث")
    
    return ConversationHandler.END

async def extract_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract members from a group with confirmation"""
    if update.message.from_user.id != ADMIN_ID:
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
    
    if query.from_user.id != ADMIN_ID:
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
            
            await log_admin_action(query.from_user.id, "extract_members", details=f"Extracted {len(members)} from {group.title}")
            
        except Exception as e:
            logger.error(f"Error extracting members: {e}")
            await query.edit_message_text("❌ حدث خطأ أثناء استخراج الأعضاء. الرجاء المحاولة لاحقًا.")
    else:
        await query.edit_message_text("❌ تم إلغاء عملية الاستخراج")
    
    return ConversationHandler.END

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin reply to user with confirmation"""
    if update.message.from_user.id != ADMIN_ID:
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
        f"⚠️ هل أنت متأكد من أنك تريد إرسال هذه الرسالة إلى المستخدم {user_id}؟\n\n"
        f"محتوى الرسالة:\n{message}",
        reply_markup=reply_markup
    )
    return "confirm_reply"

async def confirm_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and send admin reply"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    if query.data == "confirm_reply":
        reply_data = context.user_data.get('admin_reply')
        
        try:
            await context.bot.send_message(
                chat_id=reply_data['user_id'],
                text=f"📨 رد من الإدارة:\n\n{reply_data['message']}"
            )
            await query.edit_message_text("✅ تم إرسال الرد")
            
            await log_admin_action(query.from_user.id, "admin_reply", reply_data['user_id'])
            
        except Exception as e:
            logger.error(f"Error replying to {reply_data['user_id']}: {e}")
            await query.edit_message_text("❌ فشل إرسال الرد")
    else:
        await query.edit_message_text("❌ تم إلغاء إرسال الرد")
    
    return ConversationHandler.END

async def import_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Import users from Excel with confirmation"""
    if update.message.from_user.id != ADMIN_ID:
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
    
    if query.from_user.id != ADMIN_ID:
        return
    
    if query.data == "confirm_import":
        filename = context.user_data.get('import_file')
        
        try:
            await query.edit_message_text("🔄 Processing your file...")
            
            # Read Excel with enhanced validation
            df = pd.read_excel(filename)
            required_columns = ['id', 'username', 'name', 'telegram_id']
            
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
                        user_id = int(row['id'])
                        user_ids.append(user_id)
                        
                        await db.execute(
                            """INSERT OR REPLACE INTO users 
                            (id, username, name, age, bio, type, 
                             location, photo, country, city,
                             telegram_id, banned, frozen, admin)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                user_id,
                                str(row.get('username', '')),
                                str(row.get('name', '')),
                                int(row.get('age', 0)),
                                str(row.get('bio', '')),
                                str(row.get('type', '')),
                                str(row.get('location', '')),
                                str(row.get('photo', '')),
                                str(row.get('country', '')),
                                str(row.get('city', '')),
                                int(row['telegram_id']),
                                int(row.get('banned', 0)),
                                int(row.get('frozen', 0)),
                                int(row.get('admin', 0))
                            )
                        )
                        success += 1
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
                    f"SELECT COUNT(*) FROM users WHERE id IN ({','.join(map(str, user_ids))})"
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
                chat_id=ADMIN_ID,
                text="Would you like to verify the current database state?",
                reply_markup=reply_markup
            )
            
            await log_admin_action(query.from_user.id, "import_users", details=f"Imported {success} users")
            
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
    if update.message.from_user.id != ADMIN_ID:
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
    
    if query.from_user.id != ADMIN_ID:
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
                    chat_id=ADMIN_ID,
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
                chat_id=ADMIN_ID,
                document=output,
                filename=f"database_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
                caption="📤 Full database export"
            )
            
        await query.edit_message_text("✅ Database exported successfully")
        
        await log_admin_action(query.from_user.id, "export_verification")
        
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        await query.edit_message_text("❌ Failed to export database")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user with confirmation"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
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
    
    if query.from_user.id != ADMIN_ID:
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
    
    if query.from_user.id != ADMIN_ID:
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
    
    if query.from_user.id != ADMIN_ID:
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
    
    if query.from_user.id != ADMIN_ID:
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
    
    if query.from_user.id != ADMIN_ID:
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
    
    if query.from_user.id != ADMIN_ID:
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

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "مرحبًا بك في البوت الرئيسي",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 بحث", callback_data="search")],
            [InlineKeyboardButton("📝 ملاحظات", callback_data="feedback")],
            [InlineKeyboardButton("⚠️ إبلاغ", callback_data="report")]
        ])
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
    handlers = [
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
        CallbackQueryHandler(main_menu, pattern="^main_menu$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast)
    ]
    
    for handler in handlers:
        application.add_handler(handler)

    # Set bot commands
    await set_bot_commands(application)
    await application.run_polling()

if __name__ == '__main__':
    async def run():
        await init_db()
        await main()
    
    asyncio.run(run())
