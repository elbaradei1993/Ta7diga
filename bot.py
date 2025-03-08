import logging
import asyncio
import nest_asyncio
import aiosqlite
import uuid
import math
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
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"
DATABASE = "users.db"

# Helper function to calculate distance between two coordinates
def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine formula to calculate distance in kilometers
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 
         + math.cos(math.radians(lat1)) 
         * math.cos(math.radians(lat2)) 
         * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Database initialization
async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            age INTEGER,
            bio TEXT,
            type TEXT,
            lat REAL,
            lon REAL,
            photo TEXT
        )""")
        await db.commit()

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user.id,))
        if not await cursor.fetchone():
            await register_user(update, context)
            return
    await show_main_menu(update)

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✨ مرحبا! سجل نفسك أولا\nأدخل اسمك:")
    context.user_data["registration_stage"] = "name"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stage = context.user_data.get("registration_stage")
        text = update.message.text

        if stage == "name":
            context.user_data["name"] = text
            await update.message.reply_text("كم عمرك؟")
            context.user_data["registration_stage"] = "age"

        elif stage == "age":
            if not text.isdigit():
                await update.message.reply_text("يرجى إدخال عمر صحيح!")
                return
            context.user_data["age"] = text
            await update.message.reply_text("أخبرنا عن نفسك (نبذة قصيرة):")
            context.user_data["registration_stage"] = "bio"

        elif stage == "bio":
            context.user_data["bio"] = text
            keyboard = [[InlineKeyboardButton(t, callback_data=f"type_{t}")] 
                       for t in ["فرع", "حلوة", "منجة", "برغل"]]
            await update.message.reply_text("اختر تصنيفك:", reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data["registration_stage"] = "type"
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        if query.data.startswith("type_"):
            selected_type = query.data.split("_")[1]
            user = query.from_user
            user_data = context.user_data

            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("""INSERT INTO users 
                                  (id, username, name, age, bio, type) 
                                  VALUES (?,?,?,?,?,?)""",
                                  (user.id,
                                   user.username,
                                   user_data.get("name"),
                                   user_data.get("age"),
                                   user_data.get("bio"),
                                   selected_type))
                await db.commit()

            context.user_data.clear()
            await query.message.reply_text("✅ تم التسجيل بنجاح! يرجى مشاركة موقعك الآن.")
            await show_main_menu(query.message)

        elif query.data.startswith("view_"):
            user_id = int(query.data.split("_")[1])
            await show_user_profile(query, user_id)

    except Exception as e:
        logger.error(f"Button handling error: {e}")
        await query.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        location = update.message.location
        user = update.message.from_user
        
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET lat=?, lon=? WHERE id=?", 
                            (location.latitude, location.longitude, user.id))
            await db.commit()
        
        await update.message.reply_text("📍 تم حفظ موقعك بنجاح!")
        await show_nearby_users(update, user.id)
        await show_main_menu(update)
    except Exception as e:
        logger.error(f"Location handling error: {e}")
        await update.message.reply_text("❌ حدث خطأ في حفظ الموقع")

async def show_main_menu(update: Update):
    try:
        location_button = KeyboardButton("📍 مشاركة الموقع", request_location=True)
        reply_markup = ReplyKeyboardMarkup([[location_button]], resize_keyboard=True)
        await update.message.reply_text("اختر خيارًا:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Main menu error: {e}")

async def show_nearby_users(update: Update, user_id: int):
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Get current user's location
            cursor = await db.execute("SELECT lat, lon FROM users WHERE id=?", (user_id,))
            user_loc = await cursor.fetchone()
            
            if not user_loc or None in user_loc:
                await update.message.reply_text("❌ يرجى مشاركة موقعك أولاً")
                return

            user_lat, user_lon = user_loc

            # Get all users with locations
            cursor = await db.execute("""
                SELECT id, name, lat, lon 
                FROM users 
                WHERE id != ? 
                AND lat IS NOT NULL 
                AND lon IS NOT NULL
            """, (user_id,))
            users = await cursor.fetchall()

        if not users:
            await update.message.reply_text("⚠️ لا يوجد مستخدمين قريبين")
            return

        # Calculate distances and sort users
        nearby_users = []
        for uid, name, lat, lon in users:
            distance = calculate_distance(user_lat, user_lon, lat, lon)
            nearby_users.append((uid, name, distance))

        # Sort by distance and limit to 20 users
        nearby_users.sort(key=lambda x: x[2])
        nearby_users = nearby_users[:20]

        # Create buttons with distance
        buttons = []
        for uid, name, distance in nearby_users:
            buttons.append([InlineKeyboardButton(
                f"{name} ({distance:.1f} km)",
                callback_data=f"view_{uid}"
            )])

        await update.message.reply_text(
            "👥 المستخدمين القريبين:",
            reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Nearby users error: {e}")
        await update.message.reply_text("❌ حدث خطأ في عرض المستخدمين القريبين")

async def show_user_profile(query: Update, user_id: int):
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT name, age, bio, photo FROM users WHERE id=?", (user_id,))
            user = await cursor.fetchone()

        # Direct chat button using native Telegram URL
        buttons = [[InlineKeyboardButton(
            "💌 إرسال رسالة", 
            url=f"tg://user?id={user_id}"
        )]]

        caption = f"👤 الاسم: {user[0]}\n📅 العمر: {user[1]}\n📝 النبذة: {user[2]}"
        await query.message.reply_photo(
            photo=user[3] if user[3] else "https://via.placeholder.com/200",
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Profile show error: {e}")
        await query.message.reply_text("❌ حدث خطأ في عرض الملف الشخصي")

async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(handle_button))
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
