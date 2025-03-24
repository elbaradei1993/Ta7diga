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

# [Previous constants and database initialization remain the same...]

async def import_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced user import from Excel files"""
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

# [Previous functions remain unchanged...]

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).get_updates_pool_timeout(30).build()

    # [Previous handlers setup...]

    # Add new handlers
    application.add_handler(CommandHandler('import', import_users))
    application.add_handler(CallbackQueryHandler(export_verification, pattern="^export_verify$"))

    # [Rest of the main function remains the same...]

if __name__ == '__main__':
    asyncio.run(init_db())
    asyncio.run(main())
