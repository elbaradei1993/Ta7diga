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
ADMIN_ID = 123456789  # Replace with your Telegram user ID for admin features
PHOTO_PROMPT = "📸 يرجى إرسال صورة شخصية (اختياري):\n(يمكنك تخطي هذا الخطوة بالضغط على الزر أدناه)"
SKIP_PHOTO_BUTTON = [[InlineKeyboardButton("تخطي الصورة", callback_data="skip_photo")]]

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
        user_data = await cursor.fetchone()

    # Create inline buttons for the commands
    keyboard = [
        [InlineKeyboardButton("🛟 المساعدة", callback_data="help_command")],
        [InlineKeyboardButton("🗑️ حذف الحساب", callback_data="delete_account")],
        [InlineKeyboardButton("📝 إنشاء/تحديث الملف الشخصي", callback_data="edit_profile")],
        [InlineKeyboardButton("🚨 الإبلاغ عن مستخدم", callback_data="report_user")],
        [InlineKeyboardButton("📩 إرسال ملاحظات", callback_data="feedback")],
        [InlineKeyboardButton("📍 مشاركة الموقع", callback_data="share_location")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "✨ مرحبا! اختر أحد الخيارات التالية:",
        reply_markup=reply_markup
    )

# Handle button clicks
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        if query.data == "help_command":
            await help_command(query.message, context)
        elif query.data == "delete_account":
            await delete_account(query.message, context)
        elif query.data == "edit_profile":
            await edit_profile(query.message, context)
        elif query.data == "report_user":
            await report_user(query.message, context)
        elif query.data == "feedback":
            await feedback(query.message, context)
        elif query.data == "share_location":
            await show_main_menu(query.message)
        elif query.data.startswith("type_"):
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
            # Add photo prompt with skip option
            await query.message.reply_text(PHOTO_PROMPT, 
                                         reply_markup=InlineKeyboardMarkup(SKIP_PHOTO_BUTTON))
            context.user_data["registration_stage"] = "photo"

        elif query.data == "skip_photo":
            await query.message.reply_text("✅ يمكنك الآن مشاركة موقعك!")
            await show_main_menu(query.message)
            context.user_data.clear()

        elif query.data.startswith("view_"):
            user_id = int(query.data.split("_")[1])
            await show_user_profile(query, user_id)

    except Exception as e:
        logger.error(f"Button handling error: {e}")
        await query.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Edit profile function
async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.from_user
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user.id,))
        user_data = await cursor.fetchone()

    if user_data:
        # If the user already has a profile, allow them to update it
        await update.reply_text("✨ اختر ما تريد تحديثه:\n\n"
                              "1. الاسم\n"
                              "2. العمر\n"
                              "3. النبذة\n"
                              "4. التصنيف")
        context.user_data["update_stage"] = "choice"
    else:
        # If the user doesn't have a profile, start the registration process
        await register_user(update, context)

# Register user function
async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.reply_text("✨ مرحبا! سجل نفسك أولا\nأدخل اسمك:")
    context.user_data["registration_stage"] = "name"

# Handle messages during registration or profile update
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
                       for t in ["موجب", "سالب", "مبادل"]]
            await update.message.reply_text("اختر تصنيفك:", reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data["registration_stage"] = "type"
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Handle photo upload
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.user_data.get("registration_stage") == "photo":
            photo_file = await update.message.photo[-1].get_file()
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("UPDATE users SET photo=? WHERE id=?", 
                               (photo_file.file_id, update.message.from_user.id))
                await db.commit()
            await update.message.reply_text("✅ تم حفظ صورتك بنجاح! يرجى مشاركة موقعك الآن.")
            await show_main_menu(update.message)
            context.user_data.clear()
    except Exception as e:
        logger.error(f"Photo handling error: {e}")
        await update.message.reply_text("❌ حدث خطأ في حفظ الصورة")

# Handle location sharing
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

# Show main menu
async def show_main_menu(update: Update):
    try:
        location_button = KeyboardButton("📍 مشاركة الموقع", request_location=True)
        reply_markup = ReplyKeyboardMarkup([[location_button]], resize_keyboard=True)
        await update.message.reply_text("اختر خيارًا:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Main menu error: {e}")

# Show nearby users
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

# Show user profile
async def show_user_profile(query: Update, user_id: int):
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT name, age, bio, type, photo FROM users WHERE id=?", (user_id,))
            user = await cursor.fetchone()

        # Updated profile display with type
        caption = (f"👤 الاسم: {user[0]}\n"
                   f"📅 العمر: {user[1]}\n"
                   f"📝 النبذة: {user[2]}\n"
                   f"📌 التصنيف: {user[3]}")

        buttons = [[InlineKeyboardButton(
            "💌 إرسال رسالة", 
            url=f"tg://user?id={user_id}"
        )]]

        await query.message.reply_photo(
            photo=user[4] if user[4] else "https://via.placeholder.com/200",
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Profile show error: {e}")
        await query.message.reply_text("❌ حدث خطأ في عرض الملف الشخصي")

# Admin stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة!")
        return
    
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count = await cursor.fetchone()
    
    await update.message.reply_text(f"📊 إحصائيات البوت:\n\n👥 عدد المستخدمين: {count[0]}")

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛟 *كيفية استخدام البوت:*\n\n"
        "1. ابدأ بتسجيل بياناتك باستخدام الأمر /start.\n"
        "2. شارك موقعك لرؤية المستخدمين القريبين.\n"
        "3. تصفح ملفات المستخدمين القريبين وابدأ المحادثات.\n"
        "4. استخدم /update لتحديث ملفك الشخصي.\n"
        "5. استخدم /delete لحذف حسابك.\n"
        "6. استخدم /report للإبلاغ عن مستخدم.\n"
        "7. استخدم /feedback لإرسال ملاحظاتك.\n\n"
        "📌 يمكنك تحديث قائمة المستخدمين القريبين باستخدام زر '🔄 تحديث'."
    )
    await update.reply_text(help_text, parse_mode="Markdown")

# Delete account command
async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.from_user
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM users WHERE id=?", (user.id,))
        await db.commit()
    await update.reply_text("✅ تم حذف حسابك بنجاح!")

# Report user command
async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.reply_text("📝 الرجاء إدخال معرف المستخدم الذي تريد الإبلاغ عنه:")
    context.user_data["report_stage"] = "user_id"

# Feedback command
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.reply_text("📝 الرجاء إدخال ملاحظاتك أو اقتراحاتك:")
    context.user_data["feedback_stage"] = "message"

# Broadcast command (Admin Only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية استخدام هذا الأمر.")
        return
    await update.message.reply_text("📢 الرجاء إدخال الرسالة التي تريد بثها:")
    context.user_data["broadcast_stage"] = "message"

# Handle broadcast messages
async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        broadcast_message = update.message.text
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT id FROM users")
            users = await cursor.fetchall()
        for user in users:
            try:
                await context.bot.send_message(chat_id=user[0], text=broadcast_message)
            except Exception as e:
                logger.error(f"Failed to send broadcast to user {user[0]}: {e}")
        await update.message.reply_text("✅ تم بث الرسالة بنجاح!")
        context.user_data.clear()
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء البث، يرجى المحاولة مرة أخرى.")

# Main function
async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add all command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("delete", delete_account))
    app.add_handler(CommandHandler("update", update_profile))
    app.add_handler(CommandHandler("report", report_user))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))  # Admin stats command
    
    # Add all message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # Photo handler
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))  # Location handler
    app.add_handler(CallbackQueryHandler(handle_button))
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
