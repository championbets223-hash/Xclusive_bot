print("DEBUG: Starting")
import asyncio
import os
from pyrogram import Client, filters, enums
from pyrogram.types import Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

SOURCE_CHANNEL = int(os.getenv("SOURCE_CHANNEL"))  # Channel B - VIP posts
TARGET_CHANNEL = int(os.getenv("TARGET_CHANNEL"))  # Channel A - link exchange
WEBSITE_LINK = os.getenv("WEBSITE_LINK")           # xclusivelive.netlify.app

app = Client("funnel_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

STRIP_TYPES = {
    enums.MessageEntityType.URL,
    enums.MessageEntityType.TEXT_LINK,
    enums.MessageEntityType.MENTION,
}

exchange_mode = {}  # tracks per-channel whether #exchange mode is ON

# ─────────────────────────────────────────────
# Part 1: Forward from Channel B → Channel A
# ─────────────────────────────────────────────
@app.on_message(filters.chat(SOURCE_CHANNEL) & ~filters.service)
async def forward_from_vip(client: Client, message: Message):
    text = message.text or message.caption or ""
    if not text:
        return

    # Replace all links/usernames with your site link
    clean_text = text
    if message.entities:
        for entity in reversed(message.entities):
            if entity.type in STRIP_TYPES:
                clean_text = clean_text[:entity.offset] + clean_text[entity.offset + entity.length:]

    final_text = clean_text.strip() + f"\n\n🔗 {WEBSITE_LINK}"

    try:
        if message.photo:
            await client.send_photo(TARGET_CHANNEL, message.photo.file_id, caption=final_text)
        elif message.video:
            await client.send_video(TARGET_CHANNEL, message.video.file_id, caption=final_text)
        else:
            await client.send_message(TARGET_CHANNEL, final_text, disable_web_page_preview=False)
    except Exception as e:
        print(f"[Forward Error] {e}")


# ─────────────────────────────────────────────
# Part 2: Auto-delete exchange posts on Channel A
# ─────────────────────────────────────────────
@app.on_message(filters.chat(TARGET_CHANNEL) & ~filters.service)
async def handle_exchange_channel(client: Client, message: Message):
    text = message.text or message.caption or ""

    # Detect #exchange separator — turn on exchange mode
    if "#exchange" in text.lower():
        exchange_mode[TARGET_CHANNEL] = True
        print("[Exchange] Exchange mode activated")
        return  # Don't delete the separator post itself

    # If exchange mode is ON, schedule deletion after 5 minutes
    if exchange_mode.get(TARGET_CHANNEL):
        asyncio.create_task(delete_after_delay(client, message, delay=300))


async def delete_after_delay(client: Client, message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(message.chat.id, message.id)
        print(f"[Auto-Delete] Deleted message {message.id} after {delay}s")
    except Exception as e:
        print(f"[Delete Error] {e}")


app.run()