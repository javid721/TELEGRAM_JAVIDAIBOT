import os
import threading
import logging
import asyncio
import requests
from flask import Flask, request, jsonify
from telegram import Bot, Update

# -------------------------------
# تنظیمات محیطی
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE")

if not TELEGRAM_TOKEN or not WEBHOOK_BASE:
    raise RuntimeError("❌ کلیدهای TELEGRAM_TOKEN و WEBHOOK_BASE باید ست شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/webhook/{TELEGRAM_TOKEN}"

# -------------------------------
# کلاینت تلگرام
# -------------------------------
bot = Bot(token=TELEGRAM_TOKEN)

# -------------------------------
# لاگر
# -------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# Flask app
# -------------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Telegram Bot Test is running!", 200


@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """دریافت آپدیت از تلگرام"""
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No data"}), 400

    update = Update.de_json(data, bot)
    threading.Thread(target=lambda: asyncio.run(handle_update(update))).start()
    return jsonify({"status": "ok"}), 200


# -------------------------------
# پردازش پیام‌ها (فقط تلگرام)
# -------------------------------
async def handle_update(update: Update):
    if not update.message:
        return

    chat_id = update.message.chat.id
    text = update.message.text or ""

    try:
        if text.startswith("/start"):
            await bot.send_message(chat_id=chat_id, text="سلام 👋 این یه تست ساده است. ارتباط فعاله ✅")
        else:
            await bot.send_message(chat_id=chat_id, text=f"دریافت شد: {text}")
    except Exception as e:
        logger.error(f"❌ handle_update error: {e}")


# -------------------------------
# تنظیم Webhook
# -------------------------------
def set_webhook():
    try:
        res = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            params={"url": WEBHOOK_URL}
        )
        if res.status_code == 200:
            logger.info(f"🚀 Webhook set to: {WEBHOOK_URL}")
        else:
            logger.error(f"⚠️ setWebhook failed: {res.text}")
    except Exception as e:
        logger.error(f"⚠️ set_webhook exception: {e}")


# -------------------------------
# اجرای برنامه
# -------------------------------
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
