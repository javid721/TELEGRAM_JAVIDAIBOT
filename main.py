import os
import threading
import logging
import asyncio
import requests
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
# ✅ افزایش pool برای جلوگیری از خطای Pool timeout
request_config = HTTPXRequest(
    connection_pool_size=50,   # پیش‌فرض 10 است، اینجا افزایش دادیم
    connect_timeout=10.0,
    read_timeout=30.0,
    write_timeout=30.0,
    pool_timeout=15.0,
)
bot = Bot(token=TELEGRAM_TOKEN, request=request_config)

client = OpenAI(api_key=OPENAI_API_KEY)
#MODEL = "gpt-3.5-turbo"
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
# Flask route
# -------------------------------
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = request.get_json()
        asyncio.run(handle_update(update))
        return "OK", 200
    except Exception as e:
        import traceback
        print("❌ Webhook Error:", e)
        traceback.print_exc()
        return "Internal Server Error", 500



# -------------------------------
# ارتباط با OpenAI
# -------------------------------
def ask_openai(prompt: str) -> str:
    """ارسال پیام به OpenAI و دریافت پاسخ"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        if "insufficient_quota" in str(e) or "429" in str(e):
            logger.error("🚫 محدودیت استفاده از OpenAI پر شده است.")
            return "🚫 متأسفم، سهمیه‌ی استفاده از OpenAI تموم شده. لطفاً بعداً دوباره امتحان کنید یا billing رو فعال کنید."
        logger.error(f"⚠️ خطا در ارتباط با OpenAI: {e}")
        return "⚠️ خطا در ارتباط با OpenAI. لطفاً بعداً دوباره تلاش کنید."


# -------------------------------
# پردازش پیام‌های تلگرام
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
            loop = asyncio.get_event_loop()
            reply = await loop.run_in_executor(None, ask_openai, text)
            await bot.send_message(chat_id=chat_id, text=reply)
    except Exception as e:
        logger.error(f"❌ handle_update error: {e}")
        try:
            await bot.send_message(chat_id=chat_id, text="⚠️ مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")
        except:
            pass


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
print("🚀 Flask starting...", flush=True)
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
