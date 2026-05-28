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

ADMIN_ID = 1098654847

app = Client("funnel_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

STRIP_TYPES = {
    enums.MessageEntityType.URL,
    enums.MessageEntityType.TEXT_LINK,
    enums.MessageEntityType.MENTION,
    enums.MessageEntityType.BOT_COMMAND,
}

exchange_mode = {}

# ── Helpers ──────────────────────────────────────────────────────────────────

def clean_links_and_mentions(text: str, entities) -> str:
    """
    Replace all URLs, text-links, and @mentions in a message with WEBSITE_LINK.
    Works by collecting all ranges to replace, then doing a single-pass rebuild
    so overlapping / adjacent entities don't corrupt the string.
    """
    if not text:
        return text

    # 1. Collect replacement ranges from Telegram entities
    replacements = []  # list of (start, end, replacement_text)

    if entities:
        for ent in entities:
            s = ent.offset
            e = ent.offset + ent.length
            if ent.type in (enums.MessageEntityType.URL,
                            enums.MessageEntityType.MENTION):
                replacements.append((s, e, WEBSITE_LINK))
            elif ent.type == enums.MessageEntityType.TEXT_LINK:
                # keep the visible label but drop the hidden URL
                replacements.append((s, e, text[s:e]))  # label stays, link gone

    # 2. Also nuke any raw URLs the entity parser may have missed
    #    (common with t.me links that Telegram sometimes doesn't entity-tag)
    url_pattern = re.compile(
        r"(https?://\S+|t\.me/\S+|@\w+)",
        re.IGNORECASE,
    )
    for m in url_pattern.finditer(text):
        # only add if not already covered by an entity range
        already = any(s <= m.start() < e for s, e, _ in replacements)
        if not already:
            replacements.append((m.start(), m.end(), WEBSITE_LINK))

    if not replacements:
        return text

    # 3. Sort and apply — process from end to start so offsets stay valid
    replacements.sort(key=lambda x: x[0], reverse=True)
    result = text
    for start, end, repl in replacements:
        result = result[:start] + repl + result[end:]

    return result


def is_admin_post(message: Message) -> bool:
    """
    Channel posts have sender_chat, not from_user.
    We treat a message as admin-owned if it came from the channel itself
    (i.e. the channel owner posted it) OR from the explicit ADMIN_ID user.
    """
    if message.from_user and message.from_user.id == ADMIN_ID:
        return True
    # If posted by the channel itself (no specific user), treat as admin
    if message.sender_chat and message.sender_chat.id == TARGET_CHANNEL:
        return True
    return False


# ── Part 1: Forward SOURCE_CHANNEL → TARGET_CHANNEL ──────────────────────────

@app.on_message(filters.chat(SOURCE_CHANNEL) & ~filters.service)
async def forward_from_vip(client: Client, message: Message):
    text = message.text or message.caption or ""
    if not text:
        return

    entities = (
        message.caption_entities
        if (message.photo or message.video)
        else message.entities
    )

    clean_text = clean_links_and_mentions(text, entities)
    final_text = clean_text.strip() + f"\n\n🔗 {WEBSITE_LINK}"

    try:
        if message.photo:
            await client.send_photo(
                TARGET_CHANNEL, message.photo.file_id, caption=final_text
            )
        elif message.video:
            await client.send_video(
                TARGET_CHANNEL, message.video.file_id, caption=final_text
            )
        else:
            await client.send_message(
                TARGET_CHANNEL, final_text, disable_web_page_preview=False
            )
        print(f"[Forward] Sent cleaned message to target channel")
    except Exception as e:
        print(f"[Forward Error] {e}")


# ── Part 2: Auto-delete exchange posts on TARGET_CHANNEL ─────────────────────

@app.on_message(filters.chat(TARGET_CHANNEL) & ~filters.service)
async def handle_exchange_channel(client: Client, message: Message):
    text = (message.text or message.caption or "").lower()

    # Admin activates exchange mode with #exchange
    if "#exchange" in text and is_admin_post(message):
        exchange_mode[TARGET_CHANNEL] = True
        print("[Exchange] Exchange mode ACTIVATED")
        # Schedule deletion of the #exchange trigger message too (after 5 min)
        asyncio.create_task(delete_after_delay(client, message, delay=300, force=True))
        return

    # Admin deactivates exchange mode with #endexchange
    if "#endexchange" in text and is_admin_post(message):
        exchange_mode[TARGET_CHANNEL] = False
        print("[Exchange] Exchange mode DEACTIVATED")
        return

    # If exchange mode is on, schedule deletion of every non-admin post
    if exchange_mode.get(TARGET_CHANNEL):
        if is_admin_post(message):
            print(f"[Auto-Delete] Skipped admin message {message.id}")
            return
        print(f"[Auto-Delete] Scheduling deletion of message {message.id} in 300s")
        asyncio.create_task(delete_after_delay(client, message, delay=300))


async def delete_after_delay(client: Client, message: Message, delay: int, force: bool = False):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(message.chat.id, message.id)
        print(f"[Auto-Delete] Deleted message {message.id} after {delay}s")
    except Exception as e:
        print(f"[Delete Error] {e}")


app.run()
