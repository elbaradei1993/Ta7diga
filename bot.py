from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler  # Use Application instead of Dispatcher
import logging
import uuid
import os
import random

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Store users waiting for a match
waiting_users = []

# Initialize Telegram bot
TELEGRAM_TOKEN = os.environ.get("7332555745:AAEGdPx1guRECMlIjlxTvms8Xx5EFDELelU")  # Get token from environment variable
bot = Bot(token=TELEGRAM_TOKEN)

# Token mapping
tokens = {}

# Command handler for /start
async def start(update: Update, context):  # Use async for v20+
    user_id = update.effective_user.id
    token = str(uuid.uuid4())
    tokens[token] = user_id
    link = f"https://your-github-pages-url.com?token={token}"  # Replace with your frontend URL
    await update.message.reply_text(f"Please click the link to continue: {link}")

# Set up the Application
application = Application.builder().token(TELEGRAM_TOKEN).build()  # Use Application instead of Dispatcher
application.add_handler(CommandHandler('start', start))

# Flask route for Telegram webhook
@app.route('/telegram_webhook', methods=['POST'])
async def telegram_webhook():  # Use async for v20+
    update = Update.de_json(request.get_json(), bot)
    await application.process_update(update)  # Use application.process_update
    return 'OK'

# Flask route for starting video chat
@app.route('/start_video_chat', methods=['POST'])
def start_video_chat():
    data = request.get_json()
    token = data.get('token')
    user_id = tokens.get(token)
    if not user_id:
        return jsonify({'message': 'Invalid token.'}), 400

    user = bot.get_chat(user_id)
    user_name = user.first_name
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

# Run the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
