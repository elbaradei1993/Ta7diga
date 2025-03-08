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
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"  # Replace with your bot token
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
        # Create users table (if it doesn't exist)
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            age INTEGER,
            bio TEXT,
            type TEXT,
            lat REAL,
            lon REAL,
            photo TEXT,
            last_active DATETIME  -- Track the last active time
        )""")

        # Create reports table
        await db.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            reported_user_id INTEGER,
            resolved BOOLEAN DEFAULT FALSE,  -- Track if the report is resolved
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

        # Create feedback table
        await db.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

        await db.commit()

# Update user activity
async def update_user_activity(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        await db.commit()

# Check if a user is online
async def is_user_online(user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT last_active FROM users WHERE id = ?", (user_id,))
        last_active = await cursor.fetchone()

    if not last_active or not last_active[0]:
        return False

    last_active_time = datetime.strptime(last_active[0], "%Y-%m-%d %H:%M:%S")
    return datetime.now() - last_active_time < timedelta(minutes=5)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_user_activity(update.message.from_user.id)  # Update activity
    try:
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
    except Exception as e:
        logger.error(f"Start command error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_user_activity(update.message.from_user.id)  # Update activity
    try:
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
    except Exception as e:
        logger.error(f"Help command error: {e}")
        await update.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Delete account command
async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_user_activity(update.from_user.id)  # Update activity
    try:
        user = update.from_user
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("DELETE FROM users WHERE id=?", (user.id,))
            await db.commit()
        await update.reply_text("✅ تم حذف حسابك بنجاح!")
    except Exception as e:
        logger.error(f"Delete account error: {e}")
        await update.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Report user command
async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_user_activity(update.from_user.id)  # Update activity
    try:
        await update.reply_text("📝 الرجاء إدخال معرف المستخدم الذي تريد الإبلاغ عنه:")
        context.user_data["report_stage"] = "user_id"
    except Exception as e:
        logger.error(f"Report user error: {e}")
        await update.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Feedback command
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_user_activity(update.from_user.id)  # Update activity
    try:
        await update.reply_text("📝 الرجاء إدخال ملاحظاتك أو اقتراحاتك:")
        context.user_data["feedback_stage"] = "message"
    except Exception as e:
        logger.error(f"Feedback command error: {e}")
        await update.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

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

# Admin command to view unresolved reports
async def view_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة!")
        return

    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT * FROM reports WHERE resolved = FALSE")
        reports = await cursor.fetchall()

    if not reports:
        await update.message.reply_text("⚠️ لا توجد تقارير غير محلولة حتى الآن.")
        return

    report_list = "\n".join([f"📜 التقرير ID: {r[0]}, 👤 المُبلغ: {r[1]}, 🚩 المُبلغ عنه: {r[2]}, 🕒 الوقت: {r[4]}" for r in reports])
    await update.message.reply_text(f"📜 قائمة التقارير غير المحلولة:\n\n{report_list}")

# Admin command to resolve a report
async def resolve_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة!")
        return

    try:
        report_id = context.args[0]
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE reports SET resolved = TRUE WHERE id = ?", (report_id,))
            await db.commit()

        await update.message.reply_text(f"✅ تم حل التقرير ID: {report_id}.")
    except Exception as e:
        logger.error(f"Resolve report error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")

# Admin stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه الميزة!")
        return

    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        count = await cursor.fetchone()
    
    await update.message.reply_text(f"📊 إحصائيات البوت:\n\n👥 عدد المستخدمين: {count[0]}")

# Edit profile function
async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_user_activity(update.from_user.id)  # Update activity
    try:
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
    except Exception as e:
        logger.error(f"Edit profile error: {e}")
        await update.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Register user function
async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_user_activity(update.from_user.id)  # Update activity
    try:
        await update.reply_text("✨ مرحبا! سجل نفسك أولا\nأدخل اسمك:")
        context.user_data["registration_stage"] = "name"
    except Exception as e:
        logger.error(f"Register user error: {e}")
        await update.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Handle messages during registration or profile update
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_user_activity(update.message.from_user.id)  # Update activity
    try:
        stage = context.user_data.get("registration_stage")
        report_stage = context.user_data.get("report_stage")
        feedback_stage = context.user_data.get("feedback_stage")
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
            # Create the type selection keyboard
            keyboard = [
                [InlineKeyboardButton("موجب", callback_data="type_موجب")],
                [InlineKeyboardButton("سالب", callback_data="type_سالب")],
                [InlineKeyboardButton("مبادل", callback_data="type_مبادل")]
            ]
            await update.message.reply_text(
                "اختر تصنيفك:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data["registration_stage"] = "type"  # Move to the type stage

        # Handle report user input
        elif report_stage == "user_id":
            reported_user_id = text
            if not reported_user_id.isdigit():
                await update.message.reply_text("❌ الرجاء إدخال معرف مستخدم صحيح (أرقام فقط).")
                return

            # Save the report to the database
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("INSERT INTO reports (reporter_id, reported_user_id) VALUES (?, ?)",
                                (update.message.from_user.id, int(reported_user_id)))
                await db.commit()

            await update.message.reply_text(f"✅ تم الإبلاغ عن المستخدم {reported_user_id}.")
            context.user_data.clear()  # Clear the report stage

            # Notify the admin
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚨 تم الإبلاغ عن مستخدم جديد:\n\n"
                     f"👤 المُبلغ: {update.message.from_user.id}\n"
                     f"🚩 المُبلغ عنه: {reported_user_id}"
            )

        # Handle feedback input
        elif feedback_stage == "message":
            feedback_message = text

            # Save the feedback to the database
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("INSERT INTO feedback (user_id, message) VALUES (?, ?)",
                                (update.message.from_user.id, feedback_message))
                await db.commit()

            await update.message.reply_text("✅ تم استلام ملاحظاتك. شكرًا لك!")
            context.user_data.clear()  # Clear the feedback stage

            # Notify the admin
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📩 تم استلام ملاحظات جديدة:\n\n"
                     f"👤 المستخدم: {update.message.from_user.id}\n"
                     f"📝 الملاحظات: {feedback_message}"
            )

    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Handle photo upload
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update_user_activity(update.message.from_user.id)  # Update activity
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
    await update_user_activity(update.message.from_user.id)  # Update activity
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
    await update_user_activity(update.message.from_user.id)  # Update activity
    try:
        location_button = KeyboardButton("📍 مشاركة الموقع", request_location=True)
        reply_markup = ReplyKeyboardMarkup([[location_button]], resize_keyboard=True)
        await update.message.reply_text("اختر خيارًا:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Main menu error: {e}")

# Show nearby users
async def show_nearby_users(update: Update, user_id: int):
    await update_user_activity(update.message.from_user.id)  # Update activity
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
            online_status = "🟢" if await is_user_online(uid) else "🔴"
            nearby_users.append((uid, name, distance, online_status))

        # Sort by distance and limit to 20 users
        nearby_users.sort(key=lambda x: x[2])
        nearby_users = nearby_users[:20]

        # Create buttons with distance and online status
        buttons = []
        for uid, name, distance, online_status in nearby_users:
            buttons.append([InlineKeyboardButton(
                f"{online_status} {name} ({distance:.1f} km)",
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
    await update_user_activity(query.from_user.id)  # Update activity
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT name, age, bio, type, photo FROM users WHERE id=?", (user_id,))
            user = await cursor.fetchone()

        # Check if the user is online
        online_status = "🟢 متصل" if await is_user_online(user_id) else "🔴 غير متصل"

        # Updated profile display with type and online status
        caption = (f"👤 الاسم: {user[0]}\n"
                   f"📅 العمر: {user[1]}\n"
                   f"📝 النبذة: {user[2]}\n"
                   f"📌 التصنيف: {user[3]}\n"
                   f"🕒 الحالة: {online_status}")

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

# Main function
async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add all command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("delete", delete_account))
    app.add_handler(CommandHandler("update", edit_profile))  # Fixed: Changed update_profile to edit_profile
    app.add_handler(CommandHandler("report", report_user))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))  # Admin stats command
    app.add_handler(CommandHandler("reports", view_reports))  # Admin command to view reports
    app.add_handler(CommandHandler("resolve", resolve_report))  # Admin command to resolve reports
    
    # Add all message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # Photo handler
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))  # Location handler
    app.add_handler(CallbackQueryHandler(handle_button))
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
