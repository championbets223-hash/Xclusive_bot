import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("856a377f205f826e152f26e8811273ab")
BOT_TOKEN = os.getenv("8870716064:AAEmirIH2LjcnyRqAxzuQvdXhoCQ-wBE-KQ")

SOURCE_CHANNEL = int(os.getenv("SOURCE_CHANNEL")) # Channel B ID
TARGET_CHANNEL = int(os.getenv("-1001331429198"))  # Channel A ID
WEBSITE_LINK = os.getenv("xclusivelive.netlify.app")           # Your VIP link

app = Client("funnel_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.chat(SOURCE_CHANNEL) & ~filters.service)
async def forward_clean(client: Client, message: Message):
    text = message.text or message.caption
    if not text:
        return
    
    # Strip all links/usernames
    clean_text = text
    if message.entities:
        for entity in reversed(message.entities):
            if entity.type in ["url", "text_link", "mention", "username"]:
                clean_text = clean_text[:entity.offset] + clean_text[entity.offset + entity.length:]
    
    # Add your link
    final_text = clean_text.strip() + f"\n\n{WEBSITE_LINK}"
    
    # Send to target channel
    try:
        if message.photo:
            await client.send_photo(TARGET_CHANNEL, message.photo.file_id, caption=final_text)
        elif message.video:
            await client.send_video(TARGET_CHANNEL, message.video.file_id, caption=final_text)
        else:
            await client.send_message(TARGET_CHANNEL, final_text, disable_web_page_preview=False)
        
        # Auto-delete non-admin messages in source channel
        if "#exchange" in text.lower() and not message.from_user.is_self:
            await message.delete()
            
    except Exception as e:
        print(f"Error: {e}")

app.run()
