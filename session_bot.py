# session_bot.py (FINAL ROBUST STARTUP)
import os
import asyncio
import threading
import logging
from flask import Flask
from pyrogram import Client, filters, errors
from pyrogram.types import Message

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)
@flask_app.route('/')
def health_check(): return "Session Generator Bot is alive!", 200
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# --- Environment Variable Loading ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID'))

if not BOT_TOKEN or not ADMIN_ID:
    logger.critical("FATAL: BOT_TOKEN and ADMIN_ID environment variables must be set!")
    exit()

# --- Bot and State Management ---
app = Client("session_generator_bot", bot_token=BOT_TOKEN, api_id=12345, api_hash="dummy")
admin_filter = filters.user(ADMIN_ID)
login_state = {}

# --- Command Handlers ---
@app.on_message(filters.command("start") & admin_filter)
async def start_command(client, message: Message):
    await message.reply_text(
        "👋 **Pyrogram Session String Generator**\n\n"
        "➡️ Send /generate to begin."
    )

@app.on_message(filters.command("generate") & admin_filter)
async def generate_command(client, message: Message):
    if ADMIN_ID in login_state:
        await message.reply_text("A process is already running. Send /cancel first.")
        return
    login_state[ADMIN_ID] = {"state": "awaiting_api_id"}
    await message.reply_text("**(Step 1/5)** Please send your **API_ID**.")

# (All other command handlers and the handle_login_steps function are unchanged)
# ...

# --- Main Application Start ---
async def main():
    # This is the new, more robust way to start
    await app.start()
    logger.info("Session Generator Bot started.")
    await asyncio.Event().wait() # Keep the script alive forever

if __name__ == "__main__":
    # Start Flask in a background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run the main asyncio event loop
    logger.info("Starting application...")
    asyncio.run(main())