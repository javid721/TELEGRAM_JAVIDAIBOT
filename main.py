import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
import asyncio

# -------------------------------
# تنظیمات
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE")  # مثال: "https://your-app.onrender.com"

if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not WEBHOOK_BASE:
    raise RuntimeError("TELEGRAM_TOKEN, OPENAI_API_KEY و WEBHOOK_BASE باید ست شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/{TELEGRAM_TOKEN}"

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
# Application تلگرام
# -------------------------------
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ست کردن webhook PTB
async def set_webhook():
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(WEBHOOK_URL)
    print("🚀 Webhook set to:", WEBHOOK_URL)

# -------------------------------
# Flask app
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
    # از asyncio.create_task برای async put استفاده می‌کنیم
    asyncio.create_task(application.update_queue.put(update))
    return "OK", 200

# -------------------------------
# Run محلی (اختیاری) و ست کردن webhook
# -------------------------------
if __name__ == "__main__":
    # ست کردن webhook قبل از run کردن Flask
    asyncio.run(set_webhook())

    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
