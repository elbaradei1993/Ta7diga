import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Database setup
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      user_id INTEGER PRIMARY KEY,
                      name TEXT,
                      age INTEGER,
                      bio TEXT,
                      tribe TEXT,
                      location TEXT,
                      photo TEXT)''')
    conn.commit()
    conn.close()

init_db()

def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        update.message.reply_text("أهلاً بك مجدداً! استخدم /profile لعرض ملفك الشخصي.")
    else:
        update.message.reply_text("مرحباً! لنقم بإنشاء ملفك الشخصي. ما اسمك؟")
        context.user_data['registering'] = True
        context.user_data['step'] = 'name'

# Handle profile creation steps
def handle_message(update: Update, context: CallbackContext) -> None:
    if 'registering' in context.user_data:
        user_id = update.message.from_user.id
        text = update.message.text
        step = context.user_data['step']
        
        if step == 'name':
            context.user_data['name'] = text
            update.message.reply_text("كم عمرك؟")
            context.user_data['step'] = 'age'
        elif step == 'age':
            context.user_data['age'] = text
            update.message.reply_text("اكتب نبذة قصيرة عن نفسك.")
            context.user_data['step'] = 'bio'
        elif step == 'bio':
            context.user_data['bio'] = text
            keyboard = [
                [InlineKeyboardButton("سالب", callback_data='tribe_bottom'),
                 InlineKeyboardButton("موجب", callback_data='tribe_top'),
                 InlineKeyboardButton("مبادل", callback_data='tribe_versatile')],
                [InlineKeyboardButton("🌿 فرع", callback_data="type_branch"),
                 InlineKeyboardButton("🍬 حلوة", callback_data="type_sweet")],
                [InlineKeyboardButton("🌾 برغل", callback_data="type_burghul"),
                 InlineKeyboardButton("🎭 مارق", callback_data="type_mariq")],
                [InlineKeyboardButton("🎨 شادي الديكور", callback_data="type_shady"),
                 InlineKeyboardButton("💃 بنوتي", callback_data="type_girly")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text("ما هو تصنيفك؟", reply_markup=reply_markup)
            context.user_data['step'] = 'tribe'

def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith('tribe_') or data.startswith('type_'):
        context.user_data['tribe'] = data.replace('tribe_', '').replace('type_', '')
        query.message.reply_text("تم حفظ تصنيفك! قم بإرسال موقعك الآن.")
        context.user_data['step'] = 'location'
    elif data == 'view_profiles':
        show_nearby_profiles(update, context)
    elif data.startswith('profile_'):
        show_profile(update, context, data.replace('profile_', ''))

def handle_location(update: Update, context: CallbackContext) -> None:
    if 'registering' in context.user_data and context.user_data['step'] == 'location':
        location = update.message.location
        context.user_data['location'] = f"{location.latitude},{location.longitude}"
        
        update.message.reply_text("الرجاء إرسال صورتك الشخصية.")
        context.user_data['step'] = 'photo'

def handle_photo(update: Update, context: CallbackContext) -> None:
    if 'registering' in context.user_data and context.user_data['step'] == 'photo':
        user_id = update.message.from_user.id
        photo_file = update.message.photo[-1].get_file()
        photo_path = f"{user_id}.jpg"
        photo_file.download(photo_path)
        
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, name, age, bio, tribe, location, photo) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (user_id, context.user_data['name'], context.user_data['age'], 
                        context.user_data['bio'], context.user_data['tribe'], context.user_data['location'], photo_path))
        conn.commit()
        conn.close()
        
        update.message.reply_text("تم إنشاء ملفك الشخصي بنجاح! يمكنك الآن البحث عن مستخدمين قريبين منك عبر /search")
        del context.user_data['registering']

def main():
    updater = Updater("7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak", use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.location, handle_location))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(CallbackQueryHandler(button_callback))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
