import os
import sys
import types
import threading
from flask import Flask, request, jsonify
from telegram import Bot, Update
from openai import OpenAI

# ============================================================
# ✅ رفع خطای حذف imghdr در Python 3.13
# ============================================================
if 'imghdr' not in sys.modules:
    imghdr_stub = types.ModuleType('imghdr')
    def what(file, h=None):
        return None
    imghdr_stub.what = what
    sys.modules['imghdr'] = imghdr_stub

# ============================================================
# تنظیمات محیطی
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE")  # مثل: https://telegram-javidaibot.onrender.com

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("❌ کلیدهای TELEGRAM_TOKEN و OPENAI_API_KEY باید تنظیم شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/webhook/{TELEGRAM_TOKEN}"

# ============================================================
# کلاینت‌ها
# ============================================================
bot = Bot(token=TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-3.5-turbo"

# ============================================================
# Flask App
# ============================================================
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Bot is running and webhook is active.", 200


@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """دریافت آپدیت از تلگرام و پردازش در Thread جداگانه"""
    data = request.get_json(force=True)
    if not data:
        return "No data", 400

    update = Update.de_json(data, bot)
    threading.Thread(target=handle_update, args=(update,)).start()
    return jsonify({"status": "ok"}), 200


# ============================================================
# منطق بات
# ============================================================
def ask_openai(prompt: str) -> str:
    """درخواست به OpenAI و دریافت پاسخ"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ خطا در ارتباط با OpenAI: {e}")
        return "⚠️ خطا در پاسخ از OpenAI. لطفاً بعداً دوباره تلاش کنید."


def handle_update(update: Update):
    """پردازش پیام‌های تلگرام"""
    if not update.message:
        return

    chat_id = update.message.chat.id
    text = update.message.text or ""

    try:
        if text.startswith("/start"):
            bot.send_message(chat_id=chat_id, text="سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس.")
        else:
            reply = ask_openai(text)
            bot.send_message(chat_id=chat_id, text=reply)
    except Exception as e:
        print(f"❌ handle_update error: {e}")
        bot.send_message(chat_id=chat_id, text="⚠️ مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")


# ============================================================
# Webhook Setup
# ============================================================
def set_webhook():
    import requests
    try:
        res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                           params={"url": WEBHOOK_URL})
        if res.status_code == 200:
            print("🚀 Webhook set to:", WEBHOOK_URL)
        else:
            print("⚠️ setWebhook failed:", res.text)
    except Exception as e:
        print("⚠️ set_webhook exception:", e)


# ============================================================
# Run App
# ============================================================
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
