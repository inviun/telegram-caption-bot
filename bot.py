import os
import base64
import requests
import ast
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv
import asyncio
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Logging setup (define before using `logger` below)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set. Please add BOT_TOKEN to your environment or .env file.")
    raise SystemExit("BOT_TOKEN not set")


# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB limit for uploads
RATE_LIMIT_SECONDS = 10  # One request per user every 10 seconds

# Dynamic system prompt based on platform
def get_system_prompt(platform: str) -> str:
    base_prompt = """
You are an advanced caption generation engine.
Generate 3 high-impact captions tailored for {platform}.

Rules:
- Strong hook in first line
- No clichés
- Human, authentic
- Platform-native
- Minimal emojis (0–2)
- Short and skimmable

Return ONLY a valid JSON array:
[
  {{"hook":"","body":"","cta":"","hashtags":""}}
]
"""
    platform_specs = {
        "instagram": "Instagram: Visual, engaging, story-driven.",
        "tiktok": "TikTok: Fun, trendy, short-form video style.",
        "twitter": "Twitter: Concise, witty, thread-friendly.",
        "default": "General social media: Versatile and impactful."
    }
    spec = platform_specs.get(platform.lower(), platform_specs["default"])
    return base_prompt.format(platform=spec)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ Advanced Caption Bot\n\n"
        "Send text, an image, or a video. I'll generate 3 scroll-stopping captions!\n\n"
        "Commands:\n"
        "/platform <name> - Set target platform (e.g., /platform instagram)\n"
        "/regenerate - Regenerate captions for your last input\n"
        "/help - Show this message"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)  # Reuse start message

async def set_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /platform <name> (e.g., /platform instagram)")
        return
    platform = " ".join(context.args).lower()
    context.user_data["platform"] = platform
    await update.message.reply_text(f"Platform set to: {platform.capitalize()}")

def check_rate_limit(user_data: dict) -> bool:
    """Return True if allowed, False if rate-limited.

    Uses the per-user `user_data` (provided by python-telegram-bot) to store
    the timestamp of the last request.
    """
    last_request = user_data.get("last_request")
    if last_request and datetime.now() - last_request < timedelta(seconds=RATE_LIMIT_SECONDS):
        return False
    user_data["last_request"] = datetime.now()
    return True

async def generate_captions(content: list, platform: str):
    """Generate three captions.

    If `ANTHROPIC_API_KEY` is set the function will try the Anthropic
    v1/complete endpoint and parse JSON output. On any failure it falls back
    to a compact local generator so the bot remains usable.
    """
    # Build a short context string from provided content
    text_parts = []
    for c in content:
        if c.get("type") == "text":
            text_parts.append(c.get("text", ""))
        elif c.get("type") == "image":
            text_parts.append("[image provided]")
    context_text = " ".join(text_parts).strip() or "No context provided"

    # Try Anthropic if key available
    if ANTHROPIC_API_KEY:
        prompt = get_system_prompt(platform) + "\n\nContext:\n" + context_text
        try:
            res = requests.post(
                "https://api.anthropic.com/v1/complete",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-2.1",
                    "prompt": prompt,
                    "max_tokens_to_sample": 800,
                    "temperature": 0.2,
                },
                timeout=30,
            )
            res.raise_for_status()
            data = res.json()
            completion = data.get("completion", "")
            cleaned = completion.replace("```json", "").replace("```", "").strip()
            try:
                captions = ast.literal_eval(cleaned)
            except Exception:
                captions = json.loads(cleaned)
            if isinstance(captions, list) and len(captions) == 3:
                return captions
            logger.warning("Anthropic returned unexpected format; falling back. Response: %s", cleaned)
        except Exception as e:
            logger.exception("Anthropic request failed, falling back to local generator: %s", e)

    # Local simple generator (fallback)
    captions = []
    hooks = [
        f"Make them stop scrolling — {context_text[:60]}",
        f"You won't believe this — {context_text[:60]}",
        f"Quick tip: {context_text[:60]}",
    ]
    bodies = [
        f"{context_text}. Keep it concise and add value in the first two lines.",
        f"{context_text}. Tell a short story and relate to the audience.",
        f"{context_text}. Ask a question to boost comments and engagement.",
    ]
    ctas = ["Learn more", "Save this", "Share your thoughts"]
    hashtags = ["#viral", "#tips", "#content"]

    for i in range(3):
        captions.append({
            "hook": hooks[i],
            "body": bodies[i],
            "cta": ctas[i],
            "hashtags": hashtags[i],
        })

    return captions

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_rate_limit(context.user_data):
        await update.message.reply_text("⏳ Rate limit exceeded. Please wait 10 seconds.")
        return
    
    msg = update.message
    content = []
    platform = context.user_data.get("platform", "default")
    
    # Handle text
    if msg.text and not msg.text.startswith("/"):
        content.append({"type": "text", "text": f"Context: {msg.text}"})
    
    # Handle photo
    elif msg.photo:
        file = await msg.photo[-1].get_file()
        if file.file_size > MAX_FILE_SIZE:
            await msg.reply_text("❌ Image too large (max 5MB). Please resize and try again.")
            return
        img_data = await file.download_as_bytearray()
        img_b64 = base64.b64encode(img_data).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
        })
    
    # Handle video (use thumbnail as image for analysis)
    elif msg.video:
        file = await msg.video.get_file()
        if file.file_size > MAX_FILE_SIZE:
            await msg.reply_text("❌ Video too large (max 5MB). Please shorten and try again.")
            return
        # For videos, download thumbnail if available, else treat as text description
        if msg.video.thumbnail:
            thumb_file = await msg.video.thumbnail.get_file()
            thumb_data = await thumb_file.download_as_bytearray()
            thumb_b64 = base64.b64encode(thumb_data).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": thumb_b64}
            })
        content.append({"type": "text", "text": f"Context: Video description - {msg.caption or 'No caption'}"})
    
    if not content:
        await msg.reply_text("❌ Please send text, an image, or a video.")
        return
    
    # Store last input for regeneration
    context.user_data["last_content"] = content
    
    await msg.reply_text("⏳ Generating captions...")
    try:
        captions = await generate_captions(content, platform)
        # store captions for callback handling
        context.user_data["last_captions"] = captions
        keyboard = []
        out = f"📍 Platform: {platform.capitalize()}\n\n"
        for i, c in enumerate(captions, 1):
            out += f"✨ Option {i}\n{c['hook']}\n\n{c['body']}\n{c.get('cta', '')}\n{c.get('hashtags', '')}\n\n"
            keyboard.append([InlineKeyboardButton(f"Select {i}", callback_data=f"select_{i}"),
                             InlineKeyboardButton(f"Edit {i}", callback_data=f"edit_{i}")])
        keyboard.append([InlineKeyboardButton("Regenerate All", callback_data="regenerate")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await msg.reply_text(out, reply_markup=reply_markup)
    except Exception as e:
        await msg.reply_text(f"❌ Error: {str(e)}")

async def regenerate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_rate_limit(context.user_data):
        target = update.effective_message
        if target:
            await target.reply_text("⏳ Rate limit exceeded. Please wait 10 seconds.")
        return
    
    last_content = context.user_data.get("last_content")
    if not last_content:
        target = update.effective_message
        if target:
            await target.reply_text("❌ No previous input found. Send text, image, or video first.")
        return
    
    platform = context.user_data.get("platform", "default")
    target = update.effective_message
    if target:
        await target.reply_text("⏳ Regenerating captions...")
    try:
        captions = await generate_captions(last_content, platform)
        context.user_data["last_captions"] = captions
        keyboard = []
        out = f"📍 Platform: {platform.capitalize()}\n\n"
        for i, c in enumerate(captions, 1):
            out += f"✨ Option {i}\n{c['hook']}\n\n{c['body']}\n{c.get('cta', '')}\n{c.get('hashtags', '')}\n\n"
            keyboard.append([InlineKeyboardButton(f"Select {i}", callback_data=f"select_{i}"),
                             InlineKeyboardButton(f"Edit {i}", callback_data=f"edit_{i}")])
        keyboard.append([InlineKeyboardButton("Regenerate All", callback_data="regenerate")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        if target:
            await target.reply_text(out, reply_markup=reply_markup)
    except Exception as e:
        target = update.effective_message
        if target:
            await target.reply_text(f"❌ Error: {str(e)}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    captions = context.user_data.get("last_captions")
    
    if data.startswith("select_"):
        if not captions:
            await query.edit_message_text("❌ No captions available. Send something to generate captions first.")
            return
        idx = int(data.split("_")[1]) - 1
        if idx < 0 or idx >= len(captions):
            await query.edit_message_text("❌ Invalid selection.")
            return
        selected = captions[idx]
        await query.edit_message_text(
            f"✅ Selected Caption:\n{selected['hook']}\n\n{selected['body']}\n{selected.get('cta', '')}\n{selected.get('hashtags', '')}"
        )
    elif data.startswith("edit_"):
        idx = int(data.split("_")[1]) - 1
        # For simplicity, prompt user to reply with edits (in a real app, use a form)
        await query.edit_message_text("Reply to this message with your edited caption.")
        context.user_data["editing"] = idx
    elif data == "regenerate":
        await regenerate(update, context)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("platform", set_platform))
    app.add_handler(CommandHandler("regenerate", regenerate))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
