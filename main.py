import asyncio
import os
from datetime import datetime, timedelta
import pytz
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL = int(os.getenv("TARGET_CHANNEL"))

app = Client("xclusive_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

exchange_mode = False

async def midnight_reset():
    tz = pytz.timezone("Africa/Nairobi")
    while True:
        now = datetime.now(tz)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep((midnight - now).total_seconds())
        global exchange_mode
        exchange_mode = False
        print("[Reset] Exchange mode auto-reset at midnight")

async def delete_later(client, chat_id, message_id):
    await asyncio.sleep(300)
    try:
        await client.delete_messages(chat_id, message_id)
        print(f"[Deleted] message {message_id}")
    except Exception as e:
        print(f"[Error] {e}")

@app.on_message(filters.chat(TARGET_CHANNEL) & filters.channel)
async def watch(client: Client, message: Message):
    global exchange_mode
    text = (message.text or message.caption or "").strip().lower()

    if text == "#exchange":
        exchange_mode = True
        print("[Exchange] ON")
        return

    if text == "#endexchange":
        exchange_mode = False
        print("[Exchange] OFF")
        return

    if exchange_mode:
        asyncio.create_task(delete_later(client, message.chat.id, message.id))
        print(f"[Scheduled] Delete message {message.id} in 5 min")

async def main():
    await app.start()
    asyncio.create_task(midnight_reset())
    print("Bot running...")
    await asyncio.Event().wait()

app.loop.run_until_complete(main())
