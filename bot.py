import logging
import asyncio
import nest_asyncio
import aiosqlite
import math
from datetime import datetime, timedelta
from telegram import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Location
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Configure environment
nest_asyncio.apply()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"
DATABASE = "users.db"
ADMIN_ID = 1796978458
MAX_PHOTO_SIZE = 5_000_000  # 5MB

class UserStates:
    REG_NAME = 1
    REG_AGE = 2
    REG_BIO = 3
    REG_TYPE = 4
    REG_PHOTO = 5
    REPORT_USER = 6
    FEEDBACK = 7

async def init_db():
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK(age BETWEEN 13 AND 100),
                bio TEXT NOT NULL,
                type TEXT NOT NULL,
                lat REAL CHECK(lat BETWEEN -90 AND 90),
                lon REAL CHECK(lon BETWEEN -180 AND 180),
                photo TEXT,
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            await db.execute("""CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER NOT NULL,
                reported_user_id INTEGER NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            await db.execute("""CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            await db.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")
        raise

async def db_execute(query: str, params: tuple = ()):
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(query, params)
            await db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise

async def update_user_activity(user_id: int):
    try:
        await db_execute(
            "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
    except Exception as e:
        logger.error(f"Activity update failed: {e}")

async def is_user_online(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT last_active FROM users WHERE id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            
        if not result or not result[0]:
            return False
            
        last_active = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        return datetime.now() - last_active < timedelta(minutes=5)
    except Exception as e:
        logger.error(f"Online check failed: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        context.user_data.clear()
        await update_user_activity(user.id)

        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT 1 FROM users WHERE id = ?",
                (user.id,)
            )
            exists = await cursor.fetchone()

        if not exists:
            await start_registration(update, context)
        else:
            await show_main_menu(update, context)
            
    except Exception as e:
        logger.error(f"Start error: {e}")
        await update.message.reply_text("❌ حدث خطأ في بدء التشغيل")

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("مرحبًا! لنبدأ عملية التسجيل.\nالرجاء إدخال اسمك:")
        context.user_data["state"] = UserStates.REG_NAME
    except Exception as e:
        logger.error(f"Registration start error: {e}")
        await update.message.reply_text("❌ فشل في بدء التسجيل")

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        text = update.message.text
        state = context.user_data.get("state")

        if state == UserStates.REG_NAME:
            if len(text) < 2 or any(c.isdigit() for c in text):
                await update.message.reply_text("❌ اسم غير صحيح")
                return
            context.user_data["name"] = text
            await update.message.reply_text("الرجاء إدخال عمرك:")
            context.user_data["state"] = UserStates.REG_AGE

        elif state == UserStates.REG_AGE:
            if not text.isdigit() or not 13 <= int(text) <= 100:
                await update.message.reply_text("❌ عمر غير صالح")
                return
            context.user_data["age"] = int(text)
            await update.message.reply_text("أخبرنا عن نفسك (وصف قصير):")
            context.user_data["state"] = UserStates.REG_BIO

        elif state == UserStates.REG_BIO:
            if len(text) < 10:
                await update.message.reply_text("❌ الوصف قصير جدًا")
                return
            context.user_data["bio"] = text
            keyboard = [
                [InlineKeyboardButton("موجب", callback_data="type_موجب")],
                [InlineKeyboardButton("سالب", callback_data="type_سالب")],
                [InlineKeyboardButton("مبادل", callback_data="type_مبادل")],
            ]
            
            await update.message.reply_text(
                "اختر تصنيفك:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data["state"] = UserStates.REG_TYPE

    except Exception as e:
        logger.error(f"Registration error: {e}")
        await update.message.reply_text("❌ خطأ في التسجيل")
        context.user_data.clear()

async def handle_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        selected_type = query.data.split("_")[1]
        context.user_data["type"] = selected_type
        
        await query.edit_message_text(
            "📸 يرجى إرسال صورة شخصية (اختياري):\n"
            "يمكنك تخطي هذه الخطوة بالضغط على الزر أدناه",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("تخطي الصورة", callback_data="skip_photo")]])
        )
        context.user_data["state"] = UserStates.REG_PHOTO
        
    except Exception as e:
        logger.error(f"Type selection error: {e}")
        await query.edit_message_text("❌ خطأ في اختيار التصنيف")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.user_data.get("state") != UserStates.REG_PHOTO:
            return

        photo = update.message.photo[-1]
        if photo.file_size > MAX_PHOTO_SIZE:
            await update.message.reply_text("❌ حجم الصورة كبير جدًا")
            return

        context.user_data["photo"] = photo.file_id
        await complete_registration(update, context)
        
    except Exception as e:
        logger.error(f"Photo handling error: {e}")
        await update.message.reply_text("❌ خطأ في معالجة الصورة")

async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        data = context.user_data
        
        await db_execute(
            """INSERT INTO users 
            (id, username, name, age, bio, type, photo) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user.id, user.username, data["name"], data["age"], 
             data["bio"], data["type"], data.get("photo"))
        )
        
        await update.message.reply_text("✅ تم التسجيل بنجاح!")
        await show_main_menu(update, context)
        context.user_data.clear()
        
    except Exception as e:
        logger.error(f"Registration completion error: {e}")
        await update.message.reply_text("❌ فشل في إكمال التسجيل")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            [InlineKeyboardButton("🔄 تحديث القائمة", callback_data="refresh")],
            [InlineKeyboardButton("📝 تحرير الملف الشخصي", callback_data="edit_profile")],
            [InlineKeyboardButton("🚨 الإبلاغ عن مستخدم", callback_data="report_user")],
            [InlineKeyboardButton("📩 الملاحظات والاقتراحات", callback_data="feedback")]
        ]
        
        await update.message.reply_text(
            "القائمة الرئيسية:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        await request_location(update, context)
        
    except Exception as e:
        logger.error(f"Main menu error: {e}")
        await update.message.reply_text("❌ خطأ في عرض القائمة")

async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        location_keyboard = KeyboardButton(text="📍 مشاركة الموقع", request_location=True)
        reply_markup = ReplyKeyboardMarkup([[location_keyboard]], resize_keyboard=True)
        await update.message.reply_text(
            "الرجاء مشاركة موقعك:",
            reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Location request error: {e}")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        location = update.message.location
        user = update.effective_user
        
        if not (-90 <= location.latitude <= 90) or not (-180 <= location.longitude <= 180):
            raise ValueError("Invalid coordinates")
            
        await db_execute(
            "UPDATE users SET lat = ?, lon = ? WHERE id = ?",
            (location.latitude, location.longitude, user.id))
        
        await update.message.reply_text("📍 تم تحديث موقعك!")
        await show_nearby_users(update, context)
        
    except ValueError as ve:
        logger.warning(f"Invalid location: {ve}")
        await update.message.reply_text("❌ إحداثيات غير صالحة")
    except Exception as e:
        logger.error(f"Location handling error: {e}")
        await update.message.reply_text("❌ خطأ في الموقع")

async def show_nearby_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT lat, lon FROM users WHERE id = ?",
                (user.id,))
            user_loc = await cursor.fetchone()
            
            if not user_loc or None in user_loc:
                await update.message.reply_text("❌ يرجى مشاركة موقعك")
                return

            cursor = await db.execute("""
                SELECT id, name, lat, lon 
                FROM users 
                WHERE id != ? 
                AND lat IS NOT NULL 
                AND lon IS NOT NULL
                LIMIT 50""", (user.id,))
            users = await cursor.fetchall()

        if not users:
            await update.message.reply_text("⚠️ لا يوجد مستخدمين قريبين")
            return

        buttons = []
        for uid, name, lat, lon in users:
            distance = calculate_distance(user_loc[0], user_loc[1], lat, lon)
            online = await is_user_online(uid)
            buttons.append([InlineKeyboardButton(
                f"{'🟢' if online else '🔴'} {name} ({distance:.1f} كم)",
                callback_data=f"view_{uid}")])

        await update.message.reply_text(
            "المستخدمون القريبون:",
            reply_markup=InlineKeyboardMarkup(buttons))
            
    except Exception as e:
        logger.error(f"Nearby users error: {e}")
        await update.message.reply_text("❌ خطأ في عرض المستخدمين")

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2) * math.sin(dlat/2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2) * math.sin(dlon/2))
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        user_id = int(query.data.split("_")[1])
        
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT name, age, bio, type, photo FROM users WHERE id = ?",
                (user_id,))
            profile = await cursor.fetchone()

        if not profile:
            await query.edit_message_text("❌ المستخدم غير موجود")
            return

        online_status = "🟢 متصل" if await is_user_online(user_id) else "🔴 غير متصل"
        caption = (f"👤 الاسم: {profile[0]}\n"
                   f"📅 العمر: {profile[1]}\n"
                   f"📝 الوصف: {profile[2]}\n"
                   f"📌 التصنيف: {profile[3]}\n"
                   f"🕒 الحالة: {online_status}")

        buttons = [[InlineKeyboardButton("💌 مراسلة", url=f"tg://user?id={user_id}")]]
        
        if profile[4]:
            await query.message.reply_photo(
                photo=profile[4],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query.message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(buttons))
            
    except Exception as e:
        logger.error(f"Profile view error: {e}")
        await query.edit_message_text("❌ خطأ في عرض الملف")

async def main():
    try:
        await init_db()
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(view_profile, pattern=r"^view_\d+$"))
        app.add_handler(CallbackQueryHandler(handle_type_selection, pattern=r"^type_"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_registration))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.LOCATION, handle_location))
        
        await app.run_polling()
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
