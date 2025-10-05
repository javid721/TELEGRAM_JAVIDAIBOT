import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# -------------------------------
# تنظیمات
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE")  # مثال: "https://telegram-javidaibot.onrender.com"

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("کلیدهای TELEGRAM_TOKEN و OPENAI_API_KEY باید ست شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/{TELEGRAM_TOKEN}" if WEBHOOK_BASE else None

# -------------------------------
# کلاینت OpenAI
# -------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-3.5-turbo"

async def ask_openai(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        if hasattr(resp, "choices") and resp.choices:
            choice = resp.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                return choice.message.content
            if hasattr(choice, "text"):
                return choice.text
        return str(resp)
    except Exception as e:
        return f"⚠️ خطا در ارتباط با OpenAI: {e}"

# -------------------------------
# Handlers تلگرام
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    reply = await ask_openai(text)
    await update.message.reply_text(reply)

# -------------------------------
# Flask app (Webhook)
# -------------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ Bot is running", 200

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    if not data:
        return "No data", 400
    update = Update.de_json(data, application.bot)
    # اضافه کردن update به queue
    asyncio.create_task(application.update_queue.put(update))
    return "OK", 200

# -------------------------------
# ساخت Application تلگرام
# -------------------------------
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ست کردن Webhook روی Render
if WEBHOOK_BASE:
    async def setup_webhook():
        await application.bot.delete_webhook()
        await application.bot.set_webhook(url=WEBHOOK_URL)
        print("🚀 Webhook set to:", WEBHOOK_URL)
    asyncio.run(setup_webhook())

# -------------------------------
# Run محلی (اختیاری)
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
