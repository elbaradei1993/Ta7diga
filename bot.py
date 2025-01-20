import random
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import requests

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Jitsi server URL (make sure to configure your Jitsi server here)
JITSI_SERVER = "https://meet.jit.si"

# Function to start a random video chat
def start_random_chat(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_name = update.message.from_user.first_name

    # Generate a random room name for the chat
    room_name = f"randomchat_{random.randint(1000, 9999)}"

    # Generate the Jitsi link
    jitsi_link = f"{JITSI_SERVER}/{room_name}"

    # Send the user the generated link
    update.message.reply_text(f"Hello {user_name}! You've been connected to a random chat.\n"
                              f"Click to join the video call: {jitsi_link}\n\n"
                              f"Enjoy your conversation!")

# Function to start the bot and set up commands
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome to the Random Video Chat Bot! Type /randomchat to get started.")

# Main function to set up the bot
def main():
    # Set up your bot token from the environment or your direct token
    bot_token = '7886313661:AAHIUtFWswsx8UhF8wotUh2ROHu__wkgrak'
    updater = Updater(bot_token, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("randomchat", start_random_chat))

    # Start polling for updates
    updater.start_polling()

    # Run the bot until you press Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()
