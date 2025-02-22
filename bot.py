import sqlite3
import logging
import asyncio
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Enable logging for debugging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Bot Token & Admin ID
TOKEN = "7849408417:AAGsqIedRp7hJQHlx4CMfD4TJDfhC2KssgI"
ADMIN_ID = 1796978458  # Replace with your Telegram admin ID

# Initialize bot application
app = ApplicationBuilder().token(TOKEN).build()

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("channels.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        link TEXT NOT NULL,
                        thumbnail TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Fetch channels from database
def get_channels():
    conn = sqlite3.connect("channels.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, link, thumbnail FROM channels")
    channels = cursor.fetchall()
    conn.close()
    return channels

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with available options."""
    keyboard = [
        [InlineKeyboardButton("📺 عرض القنوات", callback_data="list_channels")],
    ]
    if update.message.from_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ إدارة القنوات", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحبًا بك في تلفزيون هبوب! اختر أحد الخيارات أدناه:", reply_markup=reply_markup)

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available channels."""
    query = update.callback_query
    await query.answer()
    channels = get_channels()
    if not channels:
        await query.edit_message_text("🚫 لا توجد قنوات متاحة.")
        return
    
    response = "📺 **القنوات المتاحة:**\n"
    for ch in channels:
        response += f"{ch[0]}. [{ch[1]}]({ch[2]})\n"
    
    await query.edit_message_text(response, parse_mode="Markdown")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin panel for managing channels."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("🚫 ليس لديك صلاحية الوصول.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة قناة", callback_data="add_channel")],
        [InlineKeyboardButton("❌ إزالة قناة", callback_data="remove_channel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("⚙️ **لوحة الإدارة**\nاختر خيارًا أدناه:", parse_mode="Markdown", reply_markup=reply_markup)

async def main():
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(list_channels, pattern="^list_channels$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
