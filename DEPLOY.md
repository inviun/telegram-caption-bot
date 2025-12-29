# Deploy to Railway (Free)

**Railway** provides a free tier with $5/month in free credits — enough to run a Telegram bot.

## Setup

1. Go to [railway.app](https://railway.app) and sign up (GitHub login is easiest).

2. Create a new project > Deploy from GitHub:
   - Connect your GitHub repo or upload this folder as a new repo
   - Or: Use Railway CLI to deploy directly

3. Add environment variables in Railway dashboard:
   - `BOT_TOKEN`: Your Telegram bot token
   - `ANTHROPIC_API_KEY`: (optional) Your Anthropic API key

4. Railway will auto-detect `Procfile` and run `python bot.py`.

5. Monitor logs in Railway dashboard.

## Alternative: Deploy Locally with Windows Task Scheduler

If you have a Windows machine running 24/7:

1. Create a batch file `run_bot.bat`:
   ```batch
   @echo off
   cd /d D:\ai\bb
   .venv\Scripts\python.exe bot.py
   ```

2. Open Task Scheduler:
   - Create Basic Task > "Telegram Bot"
   - Trigger: "At log on"
   - Action: Start program `run_bot.bat`
   - Check "Run whether user is logged in or not"

3. Set `.env` with your `BOT_TOKEN`.

## Quick Railway Deploy (CLI)

```bash
npm install -g @railway/cli
railway login
railway link  # link your project
railway up    # deploy
```

Then set env vars:
```bash
railway variables set BOT_TOKEN your_token
```
