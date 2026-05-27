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
WEBSITE_LINK = os.getenv("WEBSITE_LINK"))

app = Client("funnel_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

STRIP_TYPES = {
    enums.MessageEntityType.URL,
    enums.MessageEntityType.TEXT_LINK,
    enums.MessageEntityType.MENTION,
}

@app.on_message(filters.chat(SOURCE_CHANNEL) & ~filters.service)
async def forward_clean(client: Client, message: Message):
    text = message.text or message.caption
    if not text:
        return

    # Strip links/usernames using enum comparison
    clean_text = text
    if message.entities:
        for entity in reversed(message.entities):
            if entity.type in STRIP_TYPES:
                clean_text = clean_text[:entity.offset] + clean_text[entity.offset + entity.length:]

    final_text = clean_text.strip() + f"\n\n{WEBSITE_LINK}"

    try:
        if message.photo:
            await client.send_photo(TARGET_CHANNEL, message.photo.file_id, caption=final_text)
        elif message.video:
            await client.send_video(TARGET_CHANNEL, message.video.file_id, caption=final_text)
        else:
            await client.send_message(TARGET_CHANNEL, final_text, disable_web_page_preview=False)

        # Safe auto-delete: only if it's a user message (not a channel post)
        if "#exchange" in text.lower() and message.from_user and not message.from_user.is_self:
            await message.delete()

    except Exception as e:
        print(f"Error: {e}")

app.run()