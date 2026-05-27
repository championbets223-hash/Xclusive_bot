print("DEBUG: Starting")
import asyncio
import os
from pyrogram import Client, filters, enums
from pyrogram.types import Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

SOURCE_CHANNEL = int(os.getenv("SOURCE_CHANNEL"))
TARGET_CHANNEL = int(os.getenv("TARGET_CHANNEL"))
WEBSITE_LINK = os.getenv("WEBSITE_LINK")

# ADD THIS LINE - put your ID from @userinfobot here
ADMIN_ID = 1098654847

app = Client("funnel_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

STRIP_TYPES = {
    enums.MessageEntityType.URL,
    enums.MessageEntityType.TEXT_LINK,
    enums.MessageEntityType.MENTION,
}

exchange_mode = {}

# ─────────────────────────────────────────────
# Part 1: Forward from Channel B → Channel A
# ─────────────────────────────────────────────
@app.on_message(filters.chat(SOURCE_CHANNEL) & ~filters.service)
async def forward_from_vip(client: Client, message: Message):
    text = message.text or message.caption or ""
    if not text:
        return

    clean_text = text

    entities = message.caption_entities if (message.photo or message.video) else message.entities
    if entities:
        for entity in reversed(entities):
            if entity.type in STRIP_TYPES:
                clean_text = (
                    clean_text[:entity.offset] +
                    WEBSITE_LINK +
                    clean_text[entity.offset + entity.length:]
                )

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

    if "#exchange" in text.lower():
        exchange_mode[TARGET_CHANNEL] = True
        print("[Exchange] Exchange mode activated")
        return

    if exchange_mode.get(TARGET_CHANNEL):
        asyncio.create_task(delete_after_delay(client, message, delay=300))

async def delete_after_delay(client: Client, message: Message, delay: int):
    # SKIP DELETING if message is from admin
    if message.from_user and message.from_user.id == ADMIN_ID:
        print(f"[Auto-Delete] Skipped admin message {message.id}")
        return

    # SKIP DELETING if message is the #exchange command itself
    if message.text and "#exchange" in message.text.lower():
        return

    await asyncio.sleep(delay)
    try:
        await client.delete_messages(message.chat.id, message.id)
        print(f"[Auto-Delete] Deleted message {message.id} after {delay}s")
    except Exception as e:
        print(f"[Delete Error] {e}")

app.run()