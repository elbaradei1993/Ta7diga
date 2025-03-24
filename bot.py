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
            await db.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

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
    """Show admin panel"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("📤 تصدير البيانات", callback_data="admin_export")],
        [InlineKeyboardButton("📥 استيراد البيانات", callback_data="admin_import")],
        [InlineKeyboardButton("📢 بث رسالة", callback_data="admin_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠 لوحة التحكم الإدارية:",
        reply_markup=reply_markup
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast conversation"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command")
        return
    
    await update.message.reply_text(
        "📢 الرجاء إرسال الرسالة التي تريد بثها لجميع المستخدمين:\n\n"
        "يمكنك إرسال /cancel لإلغاء الأمر."
    )
    return "broadcast"

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message"""
    if update.message.from_user.id != ADMIN_ID:
        return
    
    message = update.message.text
    if not message:
        await update.message.reply_text("❌ الرسالة فارغة")
        return "broadcast"
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT telegram_id FROM users")
            users = await cursor.fetchall()
            
        success = 0
        failed = 0
        
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
        
        await update.message.reply_text(
            f"✅ تم إرسال الرسالة إلى {success} مستخدم\n"
            f"❌ فشل الإرسال إلى {failed} مستخدم"
        )
    except Exception as e:
        logger.error(f"Error broadcasting: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء البث. الرجاء المحاولة لاحقًا.")
    
    return ConversationHandler.END

async def extract_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract members from a group"""
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
    
    try:
        await update.message.reply_text(f"⏳ جاري استخراج أعضاء {group.title}...")
        
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
        
        await update.message.reply_text(
            f"✅ تم حفظ {len(members)} عضو من {group.title}"
        )
    except Exception as e:
        logger.error(f"Error extracting members: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء استخراج الأعضاء. الرجاء المحاولة لاحقًا.")

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin reply to user"""
    if update.message.from_user.id != ADMIN_ID:
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("❌ الاستخدام: /reply <user_id> <message>")
        return
    
    user_id = int(context.args[0])
    message = " ".join(context.args[1:])
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📨 رد من الإدارة:\n\n{message}"
        )
        await update.message.reply_text("✅ تم إرسال الرد")
    except Exception as e:
        logger.error(f"Error replying to {user_id}: {e}")
        await update.message.reply_text("❌ فشل إرسال الرد")

async def import_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced user import from Excel files with detailed reporting"""
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
        
        await update.message.reply_text("🔄 Processing your file...")
        
        # Read Excel with enhanced validation
        df = pd.read_excel(filename)
        required_columns = ['id', 'username', 'name', 'telegram_id']
        
        # Validate columns
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            await update.message.reply_text(f"❌ Missing columns: {', '.join(missing)}")
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
        await update.message.reply_text("\n".join(report))
        
        # Offer to export verification
        keyboard = [
            [InlineKeyboardButton("📤 Export Current Database", callback_data="export_verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Would you like to verify the current database state?",
            reply_markup=reply_markup
        )
        
        os.remove(filename)

    except Exception as e:
        logger.error(f"Import failed: {str(e)}", exc_info=True)
        await update.message.reply_text(f"❌ Critical error: {str(e)}")
        if os.path.exists(filename):
            os.remove(filename)

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
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        await query.edit_message_text("❌ Failed to export database")

async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export all users to Excel"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command")
        return

    try:
        await update.message.reply_text("⏳ Preparing export...")
        
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
            
        await update.message.reply_text("✅ Export completed successfully")
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        await update.message.reply_text("❌ Failed to export user data")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    user_id = int(query.data.replace("ban_", ""))
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "UPDATE users SET banned = 1 WHERE telegram_id = ?",
                (user_id,)
            )
            await db.commit()
        
        await query.edit_message_text(f"✅ User {user_id} banned")
    except Exception as e:
        logger.error(f"Error banning user {user_id}: {e}")
        await query.edit_message_text(f"❌ Failed to ban user {user_id}")

async def freeze_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Freeze a user account"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    user_id = int(query.data.replace("freeze_", ""))
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "UPDATE users SET frozen = 1 WHERE telegram_id = ?",
                (user_id,)
            )
            await db.commit()
        
        await query.edit_message_text(f"✅ User {user_id} frozen")
    except Exception as e:
        logger.error(f"Error freezing user {user_id}: {e}")
        await query.edit_message_text(f"❌ Failed to freeze user {user_id}")

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote a user to admin"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    user_id = int(query.data.replace("promote_", ""))
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                "UPDATE users SET admin = 1 WHERE telegram_id = ?",
                (user_id,)
            )
            await db.commit()
        
        await query.edit_message_text(f"✅ User {user_id} promoted to admin")
    except Exception as e:
        logger.error(f"Error promoting user {user_id}: {e}")
        await query.edit_message_text(f"❌ Failed to promote user {user_id}")

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
            InlineKeyboardButton("↩️ رجوع", callback_data="admin_panel")
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
