from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler
from telegram.error import BadRequest
import logging
import uuid
import os
from dotenv import load_dotenv  # Add this line
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()  # Add this line

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Store users waiting for a match
waiting_users = []

# Initialize Telegram bot
TELEGRAM_TOKEN = os.environ.get("7332555745:AAEGdPx1guRECMlIjlxTvms8Xx5EFDELelU")  # Read token from environment variable
FRONTEND_URL = os.environ.get("https://elbaradei1993.github.io/ta7diga-bot-frontend/")  # Read frontend URL from environment variable
RAILWAY_URL = os.environ.get("https://worker-production-01b7.up.railway.app")  # Read Railway URL from environment variable

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is missing!")
if not FRONTEND_URL:
    raise ValueError("FRONTEND_URL environment variable is missing!")
if not RAILWAY_URL:
    raise ValueError("RAILWAY_URL environment variable is missing!")

bot = Bot(token=TELEGRAM_TOKEN)

# Token mapping
tokens = {}

# Command handler for /start
async def start(update: Update, context):
    user_id = update.effective_user.id
    token = str(uuid.uuid4())
    tokens[token] = user_id
    link = f"{FRONTEND_URL}?token={token}"
    await update.message.reply_text(f"Please click the link to continue: {link}")

# Set up the Application
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler('start', start))

# Flask route for Telegram webhook
@app.route('/telegram_webhook', methods=['POST'])
async def telegram_webhook():
    try:
        update = Update.de_json(request.get_json(), bot)
        await application.process_update(update)
        return 'OK'
    except Exception as e:
        logger.error(f"Error in telegram_webhook: {str(e)}")
        return jsonify({'message': 'Internal server error.'}), 500

# Flask route for starting video chat
@app.route('/start_video_chat', methods=['POST'])
def start_video_chat():
    try:
        data = request.get_json()
        token = data.get('token')
        if not token or token not in tokens:
            return jsonify({'message': 'Invalid token.'}), 400

        user_id = tokens[token]
        try:
            user = bot.get_chat(user_id)
            user_name = user.first_name
        except BadRequest as e:
            return jsonify({'message': f'Failed to fetch user details: {str(e)}'}), 400

        waiting_users.append({'user_id': user_id, 'user_name': user_name})

        if len(waiting_users) >= 2:
            user1 = waiting_users.pop(0)
            user2 = waiting_users.pop(0)
            room_name = f"random-chat-{user1['user_id']}-{user2['user_id']}"
            video_chat_link = f"https://meet.jit.si/{room_name}"

            bot.send_message(chat_id=user1['user_id'], text=f"🎥 لقد تم إقرانك مع {user2['user_name']}! اضغط هنا لبدء دردشة الفيديو: {video_chat_link}")
            bot.send_message(chat_id=user2['user_id'], text=f"🎥 لقد تم إقرانك مع {user1['user_name']}! اضغط هنا لبدء دردشة الفيديو: {video_chat_link}")

            return jsonify({'message': 'Paired with another user!', 'chat_link': video_chat_link})
        else:
            return jsonify({'message': 'Waiting for another user...'})
    except Exception as e:
        logger.error(f"Error in start_video_chat: {str(e)}")
        return jsonify({'message': 'Internal server error.'}), 500

# Run the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    # Set webhook after the app starts
    bot.set_webhook(url=f"{RAILWAY_URL}/telegram_webhook")  # Use RAILWAY_URL
