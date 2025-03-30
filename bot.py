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
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
DATABASE = os.getenv("DATABASE", "users.db")
ADMIN_ID = 1796978458  # Replace with your Telegram ID
BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# Terms and Conditions in Arabic
TERMS_AND_CONDITIONS = """
📜 **شروط وأحكام استخدام التطبيق**

1. **القبول بالشروط**:
   - باستخدام التطبيق، فإنك توافق على الالتزام بهذه الشروط.
   - يحق للإدارة تعديل الشروط عند الحاجة.

2. **شروط العضوية**:
   - يجب أن يكون عمرك 18 سنة أو أكثر.
   - يُسمح بحساب واحد فقط لكل مستخدم.

3. **المحظورات**:
   - ممنوع نشر محتوى غير لائق أو مسيء.
   - ممنوع انتحال شخصية أخرى.
   - ممنوع انتهاك خصوصية الآخرين.

4. **خصوصية البيانات**:
   - نحن نحمي بياناتك ولا نشاركها مع آخرين.
   - يمكنك طلب حذف حسابك في أي وقت.

5. **إخلاء المسؤولية**:
   - التطبيق وسيط فقط ولا نضمن سلوك الأعضاء.
   - أنت المسؤول عن تفاعلاتك مع الآخرين.

✅ **باستخدام التطبيق، أنت توافق على هذه الشروط**
"""

# List of countries and cities
COUNTRIES = {
    "السودان": ["الخرطوم", "أم درمان", "بحري", "بورتسودان", "كسلا"],
    "مصر": ["القاهرة", "الإسكندرية"],
    "السعودية": ["الرياض", "جدة"]
}

# Conversation states
TERMS, USERNAME, NAME, AGE, BIO, TYPE, COUNTRY, CITY, LOCATION, PHOTO = range(10)
FEEDBACK, REPORT = range(2)

async def init_db():
    """Initialize database with proper schema"""
    try:
        async with aiosqlite.connect(DATABASE) as db:
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
                    accepted_terms INTEGER DEFAULT 0,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            await db.commit()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

async def show_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show terms and conditions"""
    keyboard = [
        [InlineKeyboardButton("✅ أوافق على الشروط", callback_data="accept_terms")],
        [InlineKeyboardButton("❌ لا أوافق", callback_data="reject_terms")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        TERMS_AND_CONDITIONS,
        reply_markup=reply_markup
    )
    return TERMS

async def accept_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle terms acceptance"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "accept_terms":
        await query.edit_message_text(
            "شكرًا لقبولك الشروط. الرجاء إرسال اسم المستخدم الخاص بك (بدون @):"
        )
        return USERNAME
    else:
        await query.edit_message_text(
            "لا يمكنك استخدام التطبيق دون الموافقة على الشروط."
        )
        return ConversationHandler.END

# [Previous database and helper functions remain the same...]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    # Check if user already exists
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT username, banned, frozen FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            user_data = await cursor.fetchone()
        
        if user_data:
            status_msg = ""
            if user_data[1]:  # banned
                status_msg = "❌ حسابك محظور. لا يمكنك استخدام التطبيق."
            elif user_data[2]:  # frozen
                status_msg = "❄️ حسابك مجمد مؤقتًا. الرجاء التواصل مع الإدارة."
            else:
                status_msg = f"مرحبًا بك مرة أخرى @{user_data[0]}! يمكنك استخدام /search للبحث."
            
            await update.message.reply_text(status_msg)
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error checking user registration: {e}")
    
    # Show terms and conditions for new users
    return await show_terms(update, context)

# [Rest of your existing handlers...]

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
                    location, photo, country, city, 
                    telegram_id, accepted_terms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    user.id,
                    1  # Accepted terms
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

async def main():
    # Initialize database
    await init_db()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Registration handler with terms acceptance
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TERMS: [CallbackQueryHandler(accept_terms)],
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_username)],
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

    # [Add other handlers as before...]

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('terms', show_terms))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
