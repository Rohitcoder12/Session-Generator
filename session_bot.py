# session_bot.py (CORRECTED)
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
    port = int(os.environ.get("PORT", 10000)) # Render uses port 10000
    flask_app.run(host="0.0.0.0", port=port)

# --- Environment Variable Loading ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID'))

if not BOT_TOKEN or not ADMIN_ID:
    logger.critical("FATAL: BOT_TOKEN and ADMIN_ID environment variables must be set!")
    exit()

# --- Bot and State Management ---
app = Client("session_generator_bot", bot_token=BOT_TOKEN, in_memory=True)
admin_filter = filters.user(ADMIN_ID)
login_state = {}

# --- Command Handlers ---
@app.on_message(filters.command("start") & admin_filter)
async def start_command(client, message: Message):
    await message.reply_text(
        "👋 **Pyrogram Session String Generator**\n\n"
        "This bot will help you generate a session string for your user account.\n\n"
        "➡️ Send /generate to begin.\n"
        "➡️ Send /cancel at any time to stop."
    )

@app.on_message(filters.command("cancel") & admin_filter)
async def cancel_command(client, message: Message):
    if ADMIN_ID in login_state:
        del login_state[ADMIN_ID]
        await message.reply_text("✅ Process cancelled.")
    else:
        await message.reply_text("Nothing to cancel.")

@app.on_message(filters.command("generate") & admin_filter)
async def generate_command(client, message: Message):
    if ADMIN_ID in login_state:
        await message.reply_text("A process is already running. Send /cancel first.")
        return
    login_state[ADMIN_ID] = {"state": "awaiting_api_id"}
    await message.reply_text("**(Step 1/5)**\nPlease send your **API_ID**.\n\nGet it from my.telegram.org.")

# --- Main Handler for Login Steps ---
# THIS IS THE CORRECTED LINE
@app.on_message(filters.private & admin_filter & ~filters.command(["start", "cancel", "generate"]))
async def handle_login_steps(client, message: Message):
    if ADMIN_ID not in login_state:
        return
    
    state_data = login_state[ADMIN_ID]
    current_state = state_data.get("state")
    user_input = message.text

    if current_state == "awaiting_api_id":
        try:
            state_data["api_id"] = int(user_input)
            state_data["state"] = "awaiting_api_hash"
            await message.reply_text("**(Step 2/5)**\nAPI_ID saved. Now please send your **API_HASH**.")
        except ValueError:
            await message.reply_text("❌ API_ID must be a number. Please try again.")

    elif current_state == "awaiting_api_hash":
        state_data["api_hash"] = user_input
        state_data["state"] = "awaiting_phone"
        await message.reply_text("**(Step 3/5)**\nAPI_HASH saved. Now please send your **phone number** in international format (e.g., +919876543210).")

    elif current_state == "awaiting_phone":
        state_data["phone"] = user_input
        await message.reply_text("⏳ Please wait, trying to connect to Telegram...")
        
        temp_client = Client(":memory:", api_id=state_data["api_id"], api_hash=state_data["api_hash"])
        try:
            await temp_client.connect()
            sent_code = await temp_client.send_code(user_input)
            state_data["phone_code_hash"] = sent_code.phone_code_hash
            state_data["state"] = "awaiting_otp"
            await message.reply_text("**(Step 4/5)**\nAn OTP has been sent to your Telegram account. Please send it here.")
        except Exception as e:
            await message.reply_text(f"❌ **Error:** {e}\n\nProcess cancelled. Please start again with /generate.")
            del login_state[ADMIN_ID]
        finally:
            if temp_client.is_connected:
                await temp_client.disconnect()

    elif current_state == "awaiting_otp":
        state_data["otp"] = user_input
        await message.reply_text("⏳ Verifying OTP...")

        temp_client = Client(":memory:", api_id=state_data["api_id"], api_hash=state_data["api_hash"])
        try:
            await temp_client.connect()
            await temp_client.sign_in(state_data["phone"], state_data["phone_code_hash"], user_input)
            
            session_string = await temp_client.export_session_string()
            await message.reply_text(
                "✅ **Login Successful!**\n\nHere is your session string. Copy it and save it securely.\n\n"
                f"<code>{session_string}</code>"
            )
            del login_state[ADMIN_ID]

        except errors.SessionPasswordNeeded:
            state_data["state"] = "awaiting_password"
            await message.reply_text("**(Step 5/5)**\nYour account has Two-Step Verification (2FA) enabled. Please send your password.")
        except Exception as e:
            await message.reply_text(f"❌ **Error:** {e}\n\nProcess cancelled. Please start again with /generate.")
            del login_state[ADMIN_ID]
        finally:
            if temp_client.is_connected:
                await temp_client.disconnect()

    elif current_state == "awaiting_password":
        await message.reply_text("⏳ Verifying 2FA password...")

        temp_client = Client(":memory:", api_id=state_data["api_id"], api_hash=state_data["api_hash"])
        try:
            await temp_client.connect()
            await temp_client.check_password(user_input)
            
            session_string = await temp_client.export_session_string()
            await message.reply_text(
                "✅ **2FA Login Successful!**\n\nHere is your session string. Copy it and save it securely.\n\n"
                f"<code>{session_string}</code>"
            )
            del login_state[ADMIN_ID]
        except Exception as e:
            await message.reply_text(f"❌ **Error:** {e}\n\nProcess cancelled. Please start again with /generate.")
            del login_state[ADMIN_ID]
        finally:
            if temp_client.is_connected:
                await temp_client.disconnect()

# --- Main Application Start ---
if __name__ == "__main__":
    # The API_ID and HASH for the control bot itself are not needed when using in_memory=True
    # and not creating a session file on disk. But we add them for good practice.
    app.api_id = 12345 # You can use dummy values here
    app.api_hash = "dummy" 

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info("Starting Session Generator Bot...")
    app.run()