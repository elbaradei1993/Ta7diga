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
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"
DATABASE = "users.db"
ADMIN_ID = 1796978458
PHOTO_PROMPT = "📸 يرجى إرسال صورة شخصية (اختياري):\n(يمكنك تخطي هذا الخطوة بالضغط على الزر أدناه)"
SKIP_PHOTO_BUTTON = [[InlineKeyboardButton("تخطي الصورة", callback_data="skip_photo")]]
MAX_PHOTO_SIZE = 5_000_000  # 5MB

# Helper functions
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Database operations
async def init_db():
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                age INTEGER CHECK(age BETWEEN 13 AND 100),
                bio TEXT,
                type TEXT,
                lat REAL CHECK(lat BETWEEN -90 AND 90),
                lon REAL CHECK(lon BETWEEN -180 AND 180),
                photo TEXT,
                last_active DATETIME
            )""")
            await db.execute("""CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                reported_user_id INTEGER,
                resolved BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            await db.execute("""CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            await db.commit()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def update_user_activity(user_id: int):
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Activity update failed for user {user_id}: {e}")

async def is_user_online(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT last_active FROM users WHERE id = ?", (user_id,))
            last_active = await cursor.fetchone()
            
        if not last_active or not last_active[0]:
            return False
            
        last_active_time = datetime.strptime(last_active[0], "%Y-%m-%d %H:%M:%S")
        return datetime.now() - last_active_time < timedelta(minutes=5)
    except Exception as e:
        logger.error(f"Online check failed for user {user_id}: {e}")
        return False

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    try:
        await update_user_activity(update.message.from_user.id)
        user = update.message.from_user
        
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT 1 FROM users WHERE id=?", (user.id,))
            exists = await cursor.fetchone()

        keyboard = [
            [InlineKeyboardButton("🛟 المساعدة", callback_data="help_command")],
            [InlineKeyboardButton("🗑️ حذف الحساب", callback_data="delete_account")],
            [InlineKeyboardButton("📝 إنشاء/تحديث الملف الشخصي", callback_data="edit_profile")],
            [InlineKeyboardButton("🚨 الإبلاغ عن مستخدم", callback_data="report_user")],
            [InlineKeyboardButton("📩 إرسال ملاحظات", callback_data="feedback")],
            [InlineKeyboardButton("📍 مشاركة الموقع", callback_data="share_location")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✨ مرحبا! اختر أحد الخيارات التالية:", reply_markup=reply_markup)
        
        if not exists:
            await register_user(update, context)
            
    except Exception as e:
        logger.error(f"Start command error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
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
        await update.message.reply_text(help_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Help command error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("DELETE FROM users WHERE id=?", (update.message.from_user.id,))
            await db.commit()
        await update.message.reply_text("✅ تم حذف حسابك بنجاح!")
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        await update.message.reply_text("❌ فشل في حذف الحساب")

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
        context.user_data.clear()
        await update.message.reply_text("✨ اختر ما تريد تحديثه:\n\n1. الاسم\n2. العمر\n3. النبذة\n4. التصنيف")
        context.user_data["update_stage"] = "choice"
    except Exception as e:
        logger.error(f"Profile edit init failed: {e}")
        await update.message.reply_text("❌ فشل في بدء تحديث الملف الشخصي")

async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
        await update.message.reply_text("📝 الرجاء إدخال معرف المستخدم الذي تريد الإبلاغ عنه:")
        context.user_data["report_stage"] = "user_id"
    except Exception as e:
        logger.error(f"Report user error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
        await update.message.reply_text("📝 الرجاء إدخال ملاحظاتك أو اقتراحاتك:")
        context.user_data["feedback_stage"] = "message"
    except Exception as e:
        logger.error(f"Feedback command error: {e}")
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Callback handlers
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        await update_user_activity(query.from_user.id)

        if query.data == "delete_account":
            await delete_account_handler(query, context)
        elif query.data == "help_command":
            await help_command(query.message, context)
        elif query.data == "edit_profile":
            await edit_profile_handler(query, context)
        elif query.data == "report_user":
            await report_user_handler(query, context)
        elif query.data == "feedback":
            await feedback_handler(query, context)
        elif query.data == "share_location":
            await show_main_menu(query.message)
        elif query.data == "skip_photo":
            await handle_skip_photo(query, context)
        elif query.data.startswith("type_"):
            await handle_type_selection(query, context)
        elif query.data.startswith("view_"):
            await handle_profile_view(query)

    except Exception as e:
        logger.error(f"Button handling error: {e}")
        await query.edit_message_text("❌ حدث خطأ غير متوقع")

async def delete_account_handler(query: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(query.from_user.id)
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("DELETE FROM users WHERE id=?", (query.from_user.id,))
            await db.commit()
        await query.edit_message_text("✅ تم حذف حسابك بنجاح!")
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        await query.edit_message_text("❌ فشل في حذف الحساب")

async def edit_profile_handler(query: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(query.from_user.id)
        await query.edit_message_text("✨ اختر ما تريد تحديثه:\n\n1. الاسم\n2. العمر\n3. النبذة\n4. التصنيف")
        context.user_data["update_stage"] = "choice"
    except Exception as e:
        logger.error(f"Profile edit handler error: {e}")
        await query.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def report_user_handler(query: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(query.from_user.id)
        await query.edit_message_text("📝 الرجاء إدخال معرف المستخدم الذي تريد الإبلاغ عنه:")
        context.user_data["report_stage"] = "user_id"
    except Exception as e:
        logger.error(f"Report user handler error: {e}")
        await query.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def feedback_handler(query: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(query.from_user.id)
        await query.edit_message_text("📝 الرجاء إدخال ملاحظاتك أو اقتراحاتك:")
        context.user_data["feedback_stage"] = "message"
    except Exception as e:
        logger.error(f"Feedback handler error: {e}")
        await query.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def handle_skip_photo(query: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(query.from_user.id)
        await query.edit_message_text("✅ يمكنك الآن مشاركة موقعك!")
        await show_main_menu(query.message)
    except Exception as e:
        logger.error(f"Skip photo handler error: {e}")
        await query.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def handle_type_selection(query: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        selected_type = query.data.split("_")[1]
        user = query.from_user
        user_data = context.user_data

        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET type=? WHERE id=?", (selected_type, user.id))
            await db.commit()

        await query.edit_message_text(PHOTO_PROMPT, reply_markup=InlineKeyboardMarkup(SKIP_PHOTO_BUTTON))
        context.user_data["registration_stage"] = "photo"
    except Exception as e:
        logger.error(f"Type selection handler error: {e}")
        await query.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

async def handle_profile_view(query: Update):
    try:
        user_id = int(query.data.split("_")[1])
        await show_user_profile(query, user_id)
    except Exception as e:
        logger.error(f"Profile view handler error: {e}")
        await query.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")

# Message handlers
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
        text = update.message.text
        user_data = context.user_data

        if user_data.get("registration_stage") == "name":
            if len(text) < 2 or any(char.isdigit() for char in text):
                await update.message.reply_text("❌ يرجى إدخال اسم صحيح (بدون أرقام)")
                return
            user_data["name"] = text
            await update.message.reply_text("كم عمرك؟")
            user_data["registration_stage"] = "age"

        elif user_data.get("registration_stage") == "age":
            if not text.isdigit() or not (13 <= int(text) <= 100):
                await update.message.reply_text("❌ يرجى إدخال عمر صحيح بين 13 و 100 سنة!")
                return
            user_data["age"] = int(text)
            await update.message.reply_text("أخبرنا عن نفسك (نبذة قصيرة):")
            user_data["registration_stage"] = "bio"

        elif user_data.get("registration_stage") == "bio":
            if len(text) < 10:
                await update.message.reply_text("❌ يرجى إدخال نبذة تحتوي على الأقل 10 أحرف!")
                return
            user_data["bio"] = text
            keyboard = [
                [InlineKeyboardButton("موجب", callback_data="type_موجب")],
                [InlineKeyboardButton("سالب", callback_data="type_سالب")],
                [InlineKeyboardButton("مبادل", callback_data="type_مبادل")]
            ]
            await update.message.reply_text("اختر تصنيفك:", reply_markup=InlineKeyboardMarkup(keyboard))
            user_data["registration_stage"] = "type"

        elif user_data.get("report_stage") == "user_id":
            if not text.isdigit():
                await update.message.reply_text("❌ يرجى إدخال معرف مستخدم صحيح (أرقام فقط)!")
                return
            try:
                async with aiosqlite.connect(DATABASE) as db:
                    await db.execute("INSERT INTO reports (reporter_id, reported_user_id) VALUES (?, ?)",
                                    (update.message.from_user.id, int(text)))
                    await db.commit()
                await update.message.reply_text(f"✅ تم الإبلاغ عن المستخدم {text}.")
                await context.bot.send_message(
                    ADMIN_ID,
                    f"🚨 تقرير جديد:\nالمُبلغ: {update.message.from_user.id}\nالمُبلغ عنه: {text}"
                )
            except Exception as e:
                logger.error(f"Report failed: {e}")
                await update.message.reply_text("❌ فشل في تسجيل التقرير")
            finally:
                user_data.clear()

        elif user_data.get("feedback_stage") == "message":
            if len(text) < 5:
                await update.message.reply_text("❌ يرجى إدخال ملاحظات مفيدة أكثر!")
                return
            try:
                async with aiosqlite.connect(DATABASE) as db:
                    await db.execute("INSERT INTO feedback (user_id, message) VALUES (?, ?)",
                                    (update.message.from_user.id, text))
                    await db.commit()
                await update.message.reply_text("✅ تم استلام ملاحظاتك. شكرًا لك!")
                await context.bot.send_message(
                    ADMIN_ID,
                    f"📩 ملاحظات جديدة من {update.message.from_user.id}:\n{text}"
                )
            except Exception as e:
                logger.error(f"Feedback save failed: {e}")
                await update.message.reply_text("❌ فشل في حفظ الملاحظات")
            finally:
                user_data.clear()

    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
        if context.user_data.get("registration_stage") == "photo":
            photo = update.message.photo[-1]
            if photo.file_size > MAX_PHOTO_SIZE:
                await update.message.reply_text("❌ حجم الصورة كبير جدًا (الحد الأقصى 5MB)")
                return

            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("UPDATE users SET photo=? WHERE id=?", 
                               (photo.file_id, update.message.from_user.id))
                await db.commit()
            
            context.user_data.pop("registration_stage", None)
            await update.message.reply_text("✅ تم حفظ صورتك بنجاح! يرجى مشاركة موقعك الآن.")
            await show_main_menu(update.message)

    except Exception as e:
        logger.error(f"Photo handling error: {e}")
        await update.message.reply_text("❌ حدث خطأ في حفظ الصورة")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update_user_activity(update.message.from_user.id)
        location = update.message.location
        user = update.message.from_user
        
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("UPDATE users SET lat=?, lon=? WHERE id=?", 
                            (location.latitude, location.longitude, user.id))
            await db.commit()
        
        await update.message.reply_text("📍 تم حفظ موقعك بنجاح!")
        await show_nearby_users(update, user.id)

    except Exception as e:
        logger.error(f"Location handling error: {e}")
        await update.message.reply_text("❌ حدث خطأ في حفظ الموقع")

# UI components
async def show_main_menu(update: Update):
    try:
        location_button = KeyboardButton("📍 مشاركة الموقع", request_location=True)
        reply_markup = ReplyKeyboardMarkup([[location_button]], resize_keyboard=True)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text("اختر خيارًا:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("اختر خيارًا:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Main menu error: {e}")

async def show_nearby_users(update: Update, user_id: int):
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT lat, lon FROM users WHERE id=?", (user_id,))
            user_loc = await cursor.fetchone()
            
            if not user_loc or None in user_loc:
                await update.message.reply_text("❌ يرجى مشاركة موقعك أولاً")
                return

            user_lat, user_lon = user_loc
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

        nearby_users = []
        for uid, name, lat, lon in users:
            distance = calculate_distance(user_lat, user_lon, lat, lon)
            online_status = "🟢" if await is_user_online(uid) else "🔴"
            nearby_users.append((uid, name, distance, online_status))

        nearby_users.sort(key=lambda x: x[2])
        buttons = [
            [InlineKeyboardButton(
                f"{online_status} {name} ({distance:.1f} km)",
                callback_data=f"view_{uid}"
            )] for uid, name, distance, online_status in nearby_users[:20]
        ]

        await update.message.reply_text(
            "👥 المستخدمين القريبين:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"Nearby users error: {e}")
        await update.message.reply_text("❌ حدث خطأ في عرض المستخدمين القريبين")

async def show_user_profile(query: Update, user_id: int):
    try:
        await update_user_activity(query.from_user.id)
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT name, age, bio, type, photo FROM users WHERE id=?", (user_id,))
            user = await cursor.fetchone()

        if not user:
            await query.edit_message_text("❌ المستخدم غير موجود")
            return

        online_status = "🟢 متصل" if await is_user_online(user_id) else "🔴 غير متصل"
        caption = (
            f"👤 الاسم: {user[0]}\n"
            f"📅 العمر: {user[1]}\n"
            f"📝 النبذة: {user[2]}\n"
            f"📌 التصنيف: {user[3]}\n"
            f"🕒 الحالة: {online_status}"
        )

        buttons = [[InlineKeyboardButton("💌 إرسال رسالة", url=f"tg://user?id={user_id}")]]
        await query.message.reply_photo(
            photo=user[4] if user[4] else "https://via.placeholder.com/200",
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"Profile show error: {e}")
        await query.edit_message_text("❌ حدث خطأ في عرض الملف الشخصي")

# Main function
async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("delete", delete_account))
    app.add_handler(CommandHandler("update", edit_profile))
    app.add_handler(CommandHandler("report", report_user))
    app.add_handler(CommandHandler("feedback", feedback))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_button))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
