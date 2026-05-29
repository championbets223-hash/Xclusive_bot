print("DEBUG: Starting")
import asyncio
import os
import re
from pyrogram import Client, filters, enums
from pyrogram.types import Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

SOURCE_CHANNEL = int(os.getenv("SOURCE_CHANNEL"))
TARGET_CHANNEL = int(os.getenv("TARGET_CHANNEL"))
WEBSITE_LINK = os.getenv("WEBSITE_LINK", "xclusivelive.netlify.app")

app = Client("funnel_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

exchange_mode = {}

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_channel_post(message: Message) -> bool:
    """
    Returns True if the message was posted AS the channel (not by a user).
    This covers all admins posting on behalf of the channel.
    """
    if message.sender_chat and message.sender_chat.id == TARGET_CHANNEL:
        return True
    # Also cover anonymous admin posts
    if not message.from_user:
        return True
    return False


def clean_links_and_mentions(text: str, entities) -> str:
    """Replace all URLs, text-links, and @mentions with WEBSITE_LINK."""
    if not text:
        return text

    replacements = []

    if entities:
        for ent in entities:
            s = ent.offset
            e = ent.offset + ent.length
            if ent.type in (enums.MessageEntityType.URL,
                            enums.MessageEntityType.MENTION):
                replacements.append((s, e, WEBSITE_LINK))
            elif ent.type == enums.MessageEntityType.TEXT_LINK:
                replacements.append((s, e, text[s:e]))  # keep label, drop URL

    # Catch raw URLs/mentions Telegram didn't tag as entities
    url_pattern = re.compile(r"(https?://\S+|t\.me/\S+|@\w+)", re.IGNORECASE)
    for m in url_pattern.finditer(text):
        already = any(s <= m.start() < e for s, e, _ in replacements)
        if not already:
            replacements.append((m.start(), m.end(), WEBSITE_LINK))

    if not replacements:
        return text

    replacements.sort(key=lambda x: x[0], reverse=True)
    result = text
    for start, end, repl in replacements:
        result = result[:start] + repl + result[end:]
    return result


async def delete_after_delay(client: Client, message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(message.chat.id, message.id)
        print(f"[Auto-Delete] Deleted message {message.id} after {delay}s")
    except Exception as e:
        print(f"[Delete Error] {e}")


# ── Part 1: Forward SOURCE_CHANNEL → TARGET_CHANNEL ──────────────────────────

@app.on_message(filters.chat(SOURCE_CHANNEL) & ~filters.service)
async def forward_from_vip(client: Client, message: Message):
    text = message.text or message.caption or ""
    if not text:
        return

    entities = (
        message.caption_entities if (message.photo or message.video)
        else message.entities
    )

    clean_text = clean_links_and_mentions(text, entities)
    final_text = clean_text.strip() + f"\n\n🔗 {WEBSITE_LINK}"

    try:
        if message.photo:
            await client.send_photo(TARGET_CHANNEL, message.photo.file_id, caption=final_text)
        elif message.video:
            await client.send_video(TARGET_CHANNEL, message.video.file_id, caption=final_text)
        else:
            await client.send_message(TARGET_CHANNEL, final_text, disable_web_page_preview=False)
        print(f"[Forward] Sent cleaned message to target channel")
    except Exception as e:
        print(f"[Forward Error] {e}")


# ── Part 2: Auto-delete exchange posts on TARGET_CHANNEL ─────────────────────

@app.on_message(filters.chat(TARGET_CHANNEL) & ~filters.service)
async def handle_exchange_channel(client: Client, message: Message):
    text = (message.text or message.caption or "").lower()

    # ── CHANNEL POSTS (any admin posting as the channel): never deleted ──
    if is_channel_post(message):
        if "#exchange" in text:
            exchange_mode[TARGET_CHANNEL] = True
            print("[Exchange] Exchange mode ACTIVATED")
        elif "#endexchange" in text:
            exchange_mode[TARGET_CHANNEL] = False
            print("[Exchange] Exchange mode DEACTIVATED")
        return  # channel posts always stop here — never deleted

    # ── USER POSTS (exchange partners posting from personal accounts) ──
    if exchange_mode.get(TARGET_CHANNEL):
        print(f"[Auto-Delete] Scheduling deletion of user message {message.id} in 300s")
        asyncio.create_task(delete_after_delay(client, message, delay=300))


app.run()
