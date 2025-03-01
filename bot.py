import random
import logging
import asyncio
import nest_asyncio
import sqlite3
import math
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    InputMediaPhoto,
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

# Apply nest_asyncio for event loops
nest_asyncio.apply()

# Logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = "7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak"

# Database connection
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Create user profiles table with tribes (keeping original field name)
cursor.execute(
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        name TEXT,
        age INTEGER,
        bio TEXT,
        type TEXT,
        location TEXT,
        photo TEXT,
        tribes TEXT
    )"""
)
conn.commit()

ADMINS = [1796978458]  # Admin IDs

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command & enforce registration."""
    user = update.message.from_user
    cursor.execute("SELECT * FROM users WHERE id=?", (user.id,))
    result = cursor.fetchone()

    if not result:
        await update.message.reply_text("🔹 **يجب التسجيل أولًا لاستخدام البوت.**")
        await register(update, context)
        return

    keyboard = [
        [InlineKeyboardButton("🔍 حدّق", callback_data="search")],
        [InlineKeyboardButton("👥 عرض المستخدمين", callback_data="show_users")],
        [InlineKeyboardButton("📝 تعديل ملفي", callback_data="edit_profile")],
        [InlineKeyboardButton("📍 تحديث موقعي", callback_data="update_location")],
        [InlineKeyboardButton("⚙ الإعدادات", callback_data="settings")],
    ]
    
    if user.id in ADMINS:
        keyboard.append([InlineKeyboardButton("🔧 لوحة الإدارة", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌟 **مرحبًا بك في تحديقة!** اختر من القائمة:", reply_markup=reply_markup)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Guide user through registration."""
    user = update.message.from_user
    cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user.id, user.username))
    conn.commit()
    
    await update.message.reply_text("✍ **أدخل اسمك الكامل:**")
    context.user_data["register_step"] = "name"

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle registration steps."""
    user = update.message.from_user
    text = update.message.text

    step = context.user_data.get("register_step")

    if step == "name":
        cursor.execute("UPDATE users SET name=? WHERE id=?", (text, user.id))
        conn.commit()
        await update.message.reply_text("📅 **أدخل عمرك:**")
        context.user_data["register_step"] = "age"

    elif step == "age":
        cursor.execute("UPDATE users SET age=? WHERE id=?", (text, user.id))
        conn.commit()
        await update.message.reply_text("📝 **أدخل نبذة عنك:**")
        context.user_data["register_step"] = "bio"

    elif step == "bio":
        cursor.execute("UPDATE users SET bio=? WHERE id=?", (text, user.id))
        conn.commit()
        await choose_type(update)

async def choose_type(update: Update) -> None:
    """Let users choose their type (تصنيفك)."""
    keyboard = [
        [InlineKeyboardButton("🌿 فرع", callback_data="type_branch"),
         InlineKeyboardButton("🍬 حلوة", callback_data="type_sweet")],
        [InlineKeyboardButton("🌾 برغل", callback_data="type_burghul"),
         InlineKeyboardButton("🎭 مارق", callback_data="type_mariq")],
        [InlineKeyboardButton("🎨 شادي الديكور", callback_data="type_shady"),
         InlineKeyboardButton("💃 بنوتي", callback_data="type_banoti")],
        [InlineKeyboardButton("✅ حفظ", callback_data="save_type")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔖 **اختر تصنيفك:** (يمكن اختيار أكثر من واحد)", reply_markup=reply_markup)

async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save user type selections (تصنيفك)."""
    query = update.callback_query
    user_id = query.from_user.id
    selected_type = query.data.replace("type_", "")

    cursor.execute("SELECT tribes FROM users WHERE id=?", (user_id,))
    tribes = cursor.fetchone()[0] or ""

    if selected_type in tribes:
        tribes = tribes.replace(selected_type, "")
    else:
        tribes += f"{selected_type},"
        
    cursor.execute("UPDATE users SET tribes=? WHERE id=?", (tribes, user_id))
    conn.commit()
    
    await query.answer("تم تحديث التصنيف ✅")

async def save_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Finish registration process."""
    await update.callback_query.message.reply_text("📍 **يرجى مشاركة موقعك الجغرافي:** (استخدم زر المرفقات لإرسال الموقع)")
    context.user_data["register_step"] = "location"

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save user location."""
    user = update.message.from_user
    location = update.message.location
    lat_lon = f"{location.latitude},{location.longitude}"
    
    cursor.execute("UPDATE users SET location=? WHERE id=?", (lat_lon, user.id))
    conn.commit()
    
    keyboard = [
        [InlineKeyboardButton("⏩ تخطي", callback_data="skip_photo")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📸 **أرسل صورتك الشخصية الآن:** (اختياري)", reply_markup=reply_markup)
    context.user_data["register_step"] = "photo"

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save user profile picture."""
    user = update.message.from_user
    file_id = update.message.photo[-1].file_id

    cursor.execute("UPDATE users SET photo=? WHERE id=?", (file_id, user.id))
    conn.commit()

    await update.message.reply_text("✅ **تم التسجيل بنجاح! يمكنك الآن البحث عن المستخدمين القريبين.**")
    await start(update, context)

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle skipping profile photo."""
    query = update.callback_query
    user_id = query.from_user.id

    cursor.execute("UPDATE users SET photo=? WHERE id=?", ("", user_id))
    conn.commit()

    await query.answer("تم تخطي إضافة الصورة.")
    await query.message.reply_text("✅ **تم التسجيل بنجاح! يمكنك الآن البحث عن المستخدمين القريبين.**")
    await start(update, context)

def calculate_distances(user_id):
    """Calculate distances between current user and others (without geopy)."""
    cursor.execute("SELECT location FROM users WHERE id=?", (user_id,))
    current_location = cursor.fetchone()[0]
    if not current_location:
        return []
    
    current_lat, current_lon = map(float, current_location.split(','))
    
    cursor.execute("SELECT id, name, location, tribes FROM users WHERE id!=?", (user_id,))
    users = []
    for user in cursor.fetchall():
        if user[2]:
            lat, lon = map(float, user[2].split(','))
            # Simple distance calculation (approximation)
            distance = math.sqrt((current_lat - lat) ** 2 + (current_lon - lon) ** 2)
            users.append((user[0], user[1], distance, user[3]))
    
    # Sort by distance and tribe matches
    cursor.execute("SELECT tribes FROM users WHERE id=?", (user_id,))
    user_tribes = cursor.fetchone()[0] or ""
    sorted_users = sorted(
        users, 
        key=lambda x: (
            x[2],  # Sort by distance
            -len(set(user_tribes.split(',')) & set(x[3].split(',')))  # Sort by shared tribes (descending)
        )
    )
    
    return sorted_users

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Find nearby users with تصنيفك prioritization."""
    query = update.callback_query
    user_id = query.from_user.id
    
    nearby_users = calculate_distances(user_id)
    if not nearby_users:
        await query.answer("❌ لا يوجد مستخدمون بالقرب منك حاليًا.")
        return

    keyboard = [[InlineKeyboardButton(f"{user[1]} ({round(user[2],1)}km)", callback_data=f"profile_{user[0]}")] for user in nearby_users]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("🔍 **المستخدمون القريبون:**", reply_markup=reply_markup)

async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available users."""
    query = update.callback_query
    user_id = query.from_user.id
    
    cursor.execute("SELECT id, name FROM users WHERE id!=?", (user_id,))
    users = cursor.fetchall()

    if not users:
        await query.answer("❌ لا يوجد مستخدمون متاحون حاليًا.")
        return

    keyboard = [[InlineKeyboardButton(user[1], callback_data=f"profile_{user[0]}")] for user in users]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("👥 **المستخدمون المتاحون:**", reply_markup=reply_markup)

async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display selected user profile with interaction options."""
    query = update.callback_query
    user_id = int(query.data.split("_")[1])
    current_user = query.from_user.id

    cursor.execute("SELECT name, bio, age, tribes, photo FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    profile_text = (
        f"👤 الاسم: {user[0]}\n"
        f"📌 العمر: {user[2]}\n"
        f"📝 النبذة: {user[1]}\n"
        f"🌍 تصنيفك: {user[3]}"
    )
    
    # Interaction buttons
    buttons = [
        [InlineKeyboardButton("💬 محادثة", callback_data=f"chat_{user_id}")],
        [InlineKeyboardButton("👋 تاپ", callback_data=f"tap_{user_id}")]
    ]
    
    if cursor.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()[0]:
        buttons[0].append(InlineKeyboardButton("📲 دردشة مباشرة", url=f"https://t.me/{cursor.execute('SELECT username FROM users WHERE id=?', (user_id,)).fetchone()[0]}"))
    
    reply_markup = InlineKeyboardMarkup(buttons)

    await context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=user[4],
        caption=profile_text,
        reply_markup=reply_markup
    )

async def handle_tap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tapping mechanism with notifications."""
    query = update.callback_query
    tapped_user_id = int(query.data.split("_")[1])
    tapper_id = query.from_user.id

    # Get tapper's info
    cursor.execute("SELECT name, username FROM users WHERE id=?", (tapper_id,))
    tapper = cursor.fetchone()

    # Send notification to tapped user
    notification_text = f"👋 لديك تاپ جديد من {tapper[0]}!"
    keyboard = [
        [InlineKeyboardButton("💬 رد", callback_data=f"chat_{tapper_id}"),
         InlineKeyboardButton("👋 تاپ بالعكس", callback_data=f"tap_{tapper_id}")]
    ]
    if tapper[1]:
        keyboard[0].append(InlineKeyboardButton("📲 دردشة", url=f"https://t.me/{tapper[1]}"))
    
    try:
        await context.bot.send_message(
            chat_id=tapped_user_id,
            text=notification_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        await query.answer("✅ تم إرسال التاپ!")
    except Exception as e:
        await query.answer("❌ تعذر إرسال التاپ. قد يكون المستخدم حظر البوت.")

async def main():
    """Start bot with updated handlers."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(search, pattern="^search$"))
    app.add_handler(CallbackQueryHandler(show_users, pattern="^show_users$"))
    app.add_handler(CallbackQueryHandler(view_profile, pattern="^profile_"))
    app.add_handler(CallbackQueryHandler(handle_tap, pattern="^tap_"))
    app.add_handler(CallbackQueryHandler(select_type, pattern="^type_"))
    app.add_handler(CallbackQueryHandler(save_type, pattern="^save_type$"))
    app.add_handler(CallbackQueryHandler(skip_photo, pattern="^skip_photo$"))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
