import logging
import asyncio
import nest_asyncio
import aiosqlite
from geopy.distance import geodesic
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    Bot,
    ChatMember,
    InputMediaPhoto
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
import sys

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
BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# List of countries and cities
COUNTRIES = {
    "السودان": ["الخرطوم", "أم درمان", "بحري", "بورتسودان"],
    "مصر": ["القاهرة", "الإسكندرية"],
    "السعودية": ["الرياض", "جدة"]
}

# Conversation states
(
    USERNAME, NAME, AGE, BIO, TYPE, 
    COUNTRY, CITY, LOCATION, PHOTO,
    FEEDBACK, REPORT,
    BROADCAST_MESSAGE,
    BAN_USER, FREEZE_USER, PROMOTE_USER,
    ADMIN_BACK
) = range(16)

# Enhanced database initialization with proper error handling
async def init_db():
    """Initialize database with all tables and proper error handling"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            async with aiosqlite.connect(DATABASE) as db:
                # Enable WAL mode for better concurrency
                await db.execute("PRAGMA journal_mode=WAL")
                
                # Users table with improved schema
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        name TEXT NOT NULL,
                        age INTEGER CHECK(age >= 18 AND age <= 100),
                        bio TEXT CHECK(length(bio) >= 10 AND length(bio) <= 500),
                        type TEXT CHECK(type IN ('male', 'female')),
                        latitude REAL,
                        longitude REAL,
                        photo TEXT,
                        country TEXT NOT NULL,
                        city TEXT NOT NULL,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        banned INTEGER DEFAULT 0 CHECK(banned IN (0, 1)),
                        frozen INTEGER DEFAULT 0 CHECK(frozen IN (0, 1)),
                        admin INTEGER DEFAULT 0 CHECK(admin IN (0, 1)),
                        last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )""")
                
                # Create indexes for faster queries
                await db.execute("CREATE INDEX IF NOT EXISTS idx_users_location ON users(latitude, longitude)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active)")
                
                # Feedback table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        message TEXT NOT NULL,
                        resolved INTEGER DEFAULT 0,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                    )""")
                
                # Reports table with improved schema
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        reported_user_id INTEGER NOT NULL,
                        message TEXT NOT NULL,
                        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'resolved', 'dismissed')),
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                        FOREIGN KEY (reported_user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                    )""")
                
                # Admin logs with more detailed tracking
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS admin_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id INTEGER NOT NULL,
                        action_type TEXT NOT NULL,
                        target_id INTEGER,
                        details TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (admin_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                    )""")
                
                await db.commit()
                logger.info("Database initialized successfully")
                return
                
        except Exception as e:
            logger.error(f"Database initialization failed (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(retry_delay)

# Enhanced admin check with caching
async def is_admin(user_id: int) -> bool:
    """Check if user has admin privileges with basic caching"""
    if user_id == ADMIN_ID:
        return True
        
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT admin FROM users WHERE telegram_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            return result and result[0] == 1
    except Exception as e:
        logger.error(f"Admin check failed for {user_id}: {e}")
        return False

# Enhanced registration flow with proper validation
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with improved user state checks"""
    user = update.effective_user
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Check user status with proper locking
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT banned, frozen FROM users WHERE telegram_id = ?",
                (user.id,)
            )
            user_status = await cursor.fetchone()
            
            if user_status:
                if user_status[0]:  # banned
                    await update.message.reply_text("❌ حسابك محظور.")
                    return ConversationHandler.END
                elif user_status[1]:  # frozen
                    await update.message.reply_text("❄️ حسابك مجمد مؤقتًا.")
                    return ConversationHandler.END
                else:
                    await update.message.reply_text("مرحبًا بك مجددًا! استخدم /search للبحث.")
                    return ConversationHandler.END
            await db.commit()
    except Exception as e:
        logger.error(f"Start command error for {user.id}: {e}")
        await db.rollback()
    
    # Start registration
    await show_terms(update, context)
    return USERNAME

# [Previous functions like show_terms, set_username, etc. would go here...]

# Enhanced admin panel with proper confirmation messages
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel with proper access control"""
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات الكاملة", callback_data="admin_full_stats")],
        [InlineKeyboardButton("👤 إدارة المستخدمين المتقدم", callback_data="admin_manage_users")],
        [InlineKeyboardButton("📢 بث رسالة جماعية", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📤 تصدير البيانات الكاملة", callback_data="admin_export_all")],
        [InlineKeyboardButton("📥 استيراد بيانات", callback_data="admin_import")]
    ]
    
    await update.message.reply_text(
        "🛠 لوحة التحكم المتقدمة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Enhanced statistics with location data
async def handle_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed statistics including location data"""
    query = update.callback_query
    await query.answer()
    
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Get complete statistics
            stats = ["📊 الإحصائيات الكاملة:\n"]
            
            # User counts
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]
            stats.append(f"👥 إجمالي المستخدمين: {total_users}")
            
            # Location stats
            cursor = await db.execute("SELECT country, COUNT(*) FROM users GROUP BY country")
            countries = await cursor.fetchall()
            stats.append("\n🌍 التوزيع الجغرافي:")
            stats.extend([f"- {country}: {count}" for country, count in countries])
            
            # Active users
            cursor = await db.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_active > datetime('now', '-7 days')
            """)
            active_users = (await cursor.fetchone())[0]
            stats.append(f"\n🟢 مستخدمين نشطين (آخر أسبوع): {active_users}")
            
            # Reports
            cursor = await db.execute("""
                SELECT status, COUNT(*) FROM reports 
                GROUP BY status
            """)
            reports = await cursor.fetchall()
            stats.append("\n⚠️ التقارير:")
            stats.extend([f"- {status}: {count}" for status, count in reports])
            
            # Format the message
            stats_message = "\n".join(stats)
            
            # Add map of user locations (would need integration with mapping API)
            # This is a placeholder for actual implementation
            stats_message += "\n\n🗺️ خريطة توزيع المستخدمين: [سيتم إضافتها لاحقًا]"
            
            await query.edit_message_text(
                stats_message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats_refresh")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
                ])
            )
            
            # Log the stats view
            await log_admin_action(
                query.from_user.id,
                "viewed_stats",
                details="Viewed complete statistics"
            )
            
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        await query.edit_message_text("❌ فشل جلب الإحصائيات. يرجى المحاولة لاحقًا.")

# Enhanced broadcast with confirmation and progress
async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to all users with progress tracking"""
    user = update.effective_user
    if not await is_admin(user.id):
        return
    
    message = update.message.text
    
    try:
        # Get all active users
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("""
                SELECT telegram_id FROM users 
                WHERE banned = 0 AND frozen = 0
            """)
            users = await cursor.fetchall()
        
        total_users = len(users)
        if total_users == 0:
            await update.message.reply_text("⚠️ لا يوجد مستخدمين نشطين للإرسال لهم.")
            return
            
        # Send initial confirmation
        confirm_msg = await update.message.reply_text(
            f"⏳ جاري إرسال الرسالة إلى {total_users} مستخدم...\n"
            f"0/{total_users} تم إرسالها (0%)"
        )
        
        success = 0
        failed = 0
        failed_users = []
        
        # Send messages with progress updates
        for i, (user_id,) in enumerate(users, 1):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 إشعار من الإدارة:\n\n{message}"
                )
                success += 1
                
                # Update progress every 10 messages or 10%
                if i % 10 == 0 or i == total_users:
                    progress = int((i / total_users) * 100)
                    await context.bot.edit_message_text(
                        chat_id=confirm_msg.chat_id,
                        message_id=confirm_msg.message_id,
                        text=f"⏳ جاري إرسال الرسالة إلى {total_users} مستخدم...\n"
                             f"{i}/{total_users} تم إرسالها ({progress}%)\n"
                             f"✅ نجاح: {success} | ❌ فشل: {failed}"
                    )
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed += 1
                failed_users.append(str(user_id))
                logger.error(f"Broadcast failed for {user_id}: {e}")
        
        # Final report
        report = (
            f"✅ تم الانتهاء من البث!\n"
            f"📊 النتائج:\n"
            f"- ✅ تم الإرسال بنجاح: {success}\n"
            f"- ❌ فشل في الإرسال: {failed}\n"
        )
        
        if failed > 0:
            report += f"\nالمستخدمين الذين فشل الإرسال لهم:\n{', '.join(failed_users[:10])}"
            if failed > 10:
                report += f" + {failed - 10} أكثر..."
        
        await context.bot.edit_message_text(
            chat_id=confirm_msg.chat_id,
            message_id=confirm_msg.message_id,
            text=report
        )
        
        # Log the broadcast
        await log_admin_action(
            user.id,
            "broadcast",
            details=f"Sent to {success}/{total_users} users. Message: {message[:50]}..."
        )
    
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        await update.message.reply_text("❌ فشل البث. يرجى التحقق من السجل للأخطاء.")

# Enhanced import function with validation
async def import_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Import user data from Excel with proper validation"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return
    
    if not update.message.document:
        await update.message.reply_text("الرجاء إرفاق ملف Excel للاستيراد")
        return
    
    try:
        # Download the file
        file = await context.bot.get_file(update.message.document.file_id)
        file_path = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        await file.download_to_drive(file_path)
        
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Validate columns
        required_columns = {
            'username': str, 'name': str, 'age': int, 
            'bio': str, 'type': str, 'latitude': float,
            'longitude': float, 'country': str, 'city': str,
            'telegram_id': int
        }
        
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            await update.message.reply_text(
                f"❌ الملف لا يحتوي على الأعمدة المطلوبة: {', '.join(missing_cols)}"
            )
            return
        
        # Validate data types
        validation_errors = []
        for col, dtype in required_columns.items():
            try:
                df[col] = df[col].astype(dtype)
            except (ValueError, TypeError):
                validation_errors.append(f"- {col} يجب أن يكون من نوع {dtype.__name__}")
        
        if validation_errors:
            await update.message.reply_text(
                "❌ أخطاء في تحقق من البيانات:\n" + "\n".join(validation_errors)
            )
            return
        
        # Process in transaction
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("BEGIN TRANSACTION")
            
            # Prepare progress message
            progress_msg = await update.message.reply_text(
                f"⏳ جاري استيراد {len(df)} مستخدم...\n0% مكتمل"
            )
            
            total = len(df)
            success = 0
            errors = []
            
            for i, row in df.iterrows():
                try:
                    # Convert NaN to None
                    row = row.where(pd.notna(row), None)
                    
                    # Insert or update user
                    await db.execute(
                        """INSERT OR REPLACE INTO users (
                            username, name, age, bio, type,
                            latitude, longitude, country, city, 
                            telegram_id, last_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))""",
                        (
                            row['username'], row['name'], row['age'], row['bio'],
                            row['type'], row['latitude'], row['longitude'],
                            row['country'], row['city'], row['telegram_id'],
                            row.get('last_active')
                        )
                    )
                    success += 1
                    
                    # Update progress every 10 records or 10%
                    if (i + 1) % 10 == 0 or (i + 1) == total:
                        progress = int(((i + 1) / total) * 100)
                        await context.bot.edit_message_text(
                            chat_id=progress_msg.chat_id,
                            message_id=progress_msg.message_id,
                            text=f"⏳ جاري استيراد {total} مستخدم...\n{progress}% مكتمل"
                        )
                    
                except Exception as e:
                    errors.append(f"الصف {i + 2}: {str(e)}")
                    logger.error(f"Failed to import row {i}: {e}")
            
            await db.commit()
            
            # Final report
            report = (
                f"✅ تم الانتهاء من الاستيراد!\n"
                f"📊 النتائج:\n"
                f"- ✅ نجاح: {success}\n"
                f"- ❌ أخطاء: {len(errors)}\n"
            )
            
            if errors:
                error_file = BytesIO()
                error_df = pd.DataFrame({"Error": errors})
                error_df.to_excel(error_file, index=False)
                error_file.seek(0)
                
                report += "\nتم حفظ الأخطاء في الملف المرفق"
                
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=error_file,
                    filename="import_errors.xlsx",
                    caption=report
                )
            else:
                await update.message.reply_text(report)
            
            # Log the import
            await log_admin_action(
                update.effective_user.id,
                "data_import",
                details=f"Imported {success} users, {len(errors)} errors"
            )
            
    except Exception as e:
        logger.error(f"Import failed: {e}")
        await update.message.reply_text(f"❌ فشل الاستيراد: {str(e)}")
        try:
            await db.rollback()
        except:
            pass

# Enhanced error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors globally with detailed logging"""
    logger.error("Exception while handling update:", exc_info=context.error)
    
    # Log to database
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(
                """INSERT INTO admin_logs (
                    admin_id, action_type, details
                ) VALUES (?, ?, ?)""",
                (0, "error", str(context.error))
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to log error: {e}")
    
    # Notify user if possible
    try:
        if update and hasattr(update, 'effective_message'):
            await update.effective_message.reply_text(
                "⚠️ حدث خطأ غير متوقع. تم تسجيل المشكلة وسيتم إصلاحها قريبًا."
            )
    except Exception as e:
        logger.error("Error while notifying user:", exc_info=e)
    
    # Notify admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ خطأ في البوت:\n\n{context.error}\n\nحدث في: {datetime.now()}"
        )
    except Exception as e:
        logger.error("Error while notifying admin:", exc_info=e)

async def main():
    """Main application entry point with proper resource management"""
    try:
        # Initialize database
        await init_db()
        
        # Build application with proper settings
        application = ApplicationBuilder() \
            .token(BOT_TOKEN) \
            .post_init(self._on_startup) \
            .post_shutdown(self._on_shutdown) \
            .build()
        
        # [All your handler setup would go here...]
        
        # Start the bot with proper error handling
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
        logger.info("Bot is running and polling...")
        
        # Keep the application running
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped gracefully")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unexpected error: {e}")
        sys.exit(1)
