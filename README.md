# Advanced Caption Bot

This repository contains a Telegram bot that generates short social-media captions for text, images, and videos. It includes a local fallback caption generator so you can run the bot without external LLM keys.

Quick start

1. Create a virtual environment and activate it.

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

2. Install requirements

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set your `BOT_TOKEN`.

4. Run the bot

```bash
python bot.py
```

Optional: use the provided `start_bot.ps1` or `start_bot.sh` to load `.env` and run.

Notes

- To use Anthropic or other LLMs, set `ANTHROPIC_API_KEY` in `.env` and extend `generate_captions` to call the remote API.
- The bot stores temporary per-user state in `context.user_data`.
