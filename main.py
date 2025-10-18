import os
import logging
import asyncio
import requests
import traceback
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.request import HTTPXRequest
from openai import OpenAI

print("🔧 App booting up...", flush=True)

# -------------------------------
# تنظیمات محیطی
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not WEBHOOK_BASE:
    raise RuntimeError("❌ کلیدهای TELEGRAM_TOKEN, OPENAI_API_KEY و WEBHOOK_BASE باید ست شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/webhook/{TELEGRAM_TOKEN}"

# -------------------------------
# کلاینت‌ها
# -------------------------------
request_config = HTTPXRequest(
    connection_pool_size=50,
    connect_timeout=10.0,
    read_timeout=30.0,
    write_timeout=30.0,
    pool_timeout=15.0,
)
bot = Bot(token=TELEGRAM_TOKEN, request=request_config)
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"

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
    return "✅ Telegram + OpenAI bot is running!", 200

# -------------------------------
# Webhook Route
# -------------------------------
@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    """نسخه async کامل برای سازگاری با Render"""
    try:
        data = request.get_json(force=True, silent=True)
        logger.info(f"📩 Incoming webhook: {data}")

        if not data:
            return jsonify({"error": "No data"}), 400
        if "message" not in data:
            return jsonify({"status": "ignored"}), 200

        msg = data["message"]
        if "date" not in msg or "message_id" not in msg or "chat" not in msg:
            return jsonify({"status": "invalid_message"}), 200

        try:
            update = Update.de_json(data, bot)
        except Exception as e:
            logger.error(f"❌ خطا در parse کردن Update: {e}")
            traceback.print_exc()
            return jsonify({"status": "invalid_update"}), 200

        # ✅ اجرای مستقیم تابع async بدون threading
        await handle_update(update)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"❌ Exception در webhook: {e}")
        traceback.print_exc()
        return jsonify({"error": "internal error"}), 200

# -------------------------------
# ارتباط با OpenAI
# -------------------------------
def ask_openai(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        if "insufficient_quota" in str(e) or "429" in str(e):
            logger.error("🚫 محدودیت استفاده از OpenAI پر شده است.")
            return "🚫 سهمیه‌ی OpenAI تموم شده. لطفاً بعداً امتحان کنید."
        logger.error(f"⚠️ خطا در OpenAI: {e}")
        return "⚠️ خطا در ارتباط با OpenAI. لطفاً بعداً تلاش کنید."

# -------------------------------
# پردازش پیام تلگرام
# -------------------------------
async def handle_update(update: Update):
    if not update.message:
        return

    chat_id = update.message.chat.id
    text = update.message.text or ""

    try:
        if text.startswith("/start"):
            await bot.send_message(chat_id=chat_id, text="سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس 😊")
        else:
            loop = asyncio.get_running_loop()
            reply = await loop.run_in_executor(None, ask_openai, text)
            await bot.send_message(chat_id=chat_id, text=reply)
    except Exception as e:
        logger.error(f"❌ handle_update error: {e}")
        traceback.print_exc()
        try:
            await bot.send_message(chat_id=chat_id, text="⚠️ مشکلی پیش آمد. دوباره تلاش کنید.")
        except Exception:
            pass

# -------------------------------
# تنظیم Webhook
# -------------------------------
def set_webhook():
    try:
        res = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            params={"url": WEBHOOK_URL},
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
print("🚀 Flask starting...", flush=True)
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
