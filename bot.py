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
