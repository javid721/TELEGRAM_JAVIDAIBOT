import os
import threading
from flask import Flask, request, jsonify
from telegram import Bot, Update
from openai import OpenAI

# -------------------------------
# تنظیمات
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE")  # مثال: "https://telegram-javidaibot.onrender.com"

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("کلیدهای TELEGRAM_TOKEN و OPENAI_API_KEY باید ست شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/webhook/{TELEGRAM_TOKEN}" if WEBHOOK_BASE else None

# -------------------------------
# کلاینت‌ها
# -------------------------------
bot = Bot(token=TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-3.5-turbo"

# -------------------------------
# Flask App
# -------------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Bot is running ...", 200

@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """دریافت آپدیت و پردازش در Thread جداگانه"""
    data = request.get_json(force=True)
    if not data:
        return "No data", 400

    update = Update.de_json(data, bot)
    threading.Thread(target=handle_update, args=(update,)).start()
    return jsonify({"status": "ok"}), 200

# -------------------------------
# توابع اصلی
# -------------------------------
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
        return f"⚠️ خطا در ارتباط با OpenAI: {e}"

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

# -------------------------------
# ست کردن Webhook
# -------------------------------
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

# -------------------------------
# اجرای برنامه
# -------------------------------
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
