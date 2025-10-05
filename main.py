import os
from flask import Flask, request, abort
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from openai import OpenAI

# -------------------------------
# تنظیمات
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE", "")  # مثلاً "https://telegram-javidaibot.onrender.com"

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("کلیدهای TELEGRAM_TOKEN و OPENAI_API_KEY باید ست شوند!")

if not WEBHOOK_BASE:
    # اگر WEBHOOK_BASE تنظیم نشده باشد، تلاش می‌کنیم از دامنهٔ پیش‌فرض Render استفاده کنیم.
    # در Render معمولاً URL را خودت می‌دانی؛ بهتر است این متغیر را در Environment Variables تنظیم کنی.
    print("⚠️ WEBHOOK_BASE تنظیم نشده. لطفاً آن را در Environment Variables در Dashboard Render قرار بدهید.")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/{TELEGRAM_TOKEN}"

# -------------------------------
# کلاینت OpenAI
# -------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-3.5-turbo"  # اگر هزینه می‌خواهی کمتر و پایدارتر باشه از این مدل استفاده کن

def ask_openai(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        # سازگاری با ساختار response نسخه‌های مختلف openai
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            # بعضی نسخه‌ها: resp.choices[0].message.content
            choice = resp.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                return choice.message.content
            if hasattr(choice, "text"):
                return choice.text
        # fallback to str(resp)
        return str(resp)
    except Exception as e:
        return f"⚠️ خطا در ارتباط با OpenAI: {e}"

# -------------------------------
# تنظیم Bot و Dispatcher (sync)
# -------------------------------
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

def start(update, context):
    try:
        update.message.reply_text("سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس.")
    except Exception:
        pass

def handle_message(update, context):
    try:
        text = update.message.text or ""
        # تماس همزمان با OpenAI ممکن است طول بکشد؛ اینجا sync است و ممکن است تاخیر داشته باشد
        reply = ask_openai(text)
        update.message.reply_text(reply)
    except Exception as e:
        print("Error in handle_message:", e)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# -------------------------------
# Flask app (webhook endpoint)
# -------------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ Bot is running (webhook mode).", 200

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    # تلگرام پست‌ می‌کند، ساختار JSON را بخوان و پردازش کن
    if request.content_type != 'application/json':
        abort(400)
    data = request.get_json(force=True)
    if not data:
        abort(400)
    update = Update.de_json(data, bot)
    try:
        dispatcher.process_update(update)  # sync processing
    except Exception as e:
        print("❌ Error processing update:", e)
    return "OK", 200

# -------------------------------
# set webhook (at import time; acceptable در gunicorn)
# -------------------------------
try:
    # حذف webhook قبلی و ست کردن webhook جدید (بی‌خطر اگر چند بار اجرا شود)
    bot.delete_webhook()
    if WEBHOOK_BASE:
        bot.set_webhook(url=WEBHOOK_URL)
        print("🚀 Webhook set to:", WEBHOOK_URL)
    else:
        print("⚠️ WEBHOOK_BASE خالی است — webhook ست نشده.")
except Exception as e:
    print("⚠️ set_webhook failed:", e)

# -------------------------------
# Run app (for local testing)
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
