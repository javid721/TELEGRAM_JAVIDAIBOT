import os
import asyncio
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# -------------------------------
# تنظیمات
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE", "https://telegram-javidaibot.onrender.com")  # یا از ENV خوانده می‌شه

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("کلیدهای TELEGRAM_TOKEN و OPENAI_API_KEY باید ست شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE}/{TELEGRAM_TOKEN}"

# -------------------------------
# OpenAI client
# -------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"

def ask_openai(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ خطا در ارتباط با OpenAI: {e}"

# -------------------------------
# handlers
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    reply = await asyncio.to_thread(ask_openai, text)
    await update.message.reply_text(reply)

# -------------------------------
# application (telegram)
# -------------------------------
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -------------------------------
# Initialization guard (thread-safe, one-time)
# -------------------------------
_init_lock = threading.Lock()
_initialized = False

async def _init_async():
    # initialize & start the application (must be awaited)
    await application.initialize()
    await application.start()
    # حذف و ست وبهوک (اختیاری ولی مفید)
    try:
        await application.bot.delete_webhook()
    except Exception as e:
        print("⚠️ delete_webhook failed:", e)
    try:
        await application.bot.set_webhook(url=WEBHOOK_URL)
        print("✅ webhook set to", WEBHOOK_URL)
    except Exception as e:
        print("⚠️ set_webhook failed:", e)

def ensure_initialized():
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        print("⏳ initializing telegram Application...")
        # اجرا در بلاک سینک (مناسب چون routeها sync هستند)
        asyncio.run(_init_async())
        _initialized = True
        print("✅ Application initialized")

# -------------------------------
# Flask app + webhook route
# -------------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "🤖 Bot is running!", 200

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    # اگر هنوز initialize نشده، اینجا انجامش بدهیم (اولین درخواست)
    ensure_initialized()

    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    # پردازش update بصورت sync با asyncio.run
    try:
        asyncio.run(application.process_update(update))
    except Exception as e:
        # لاگ کن تا ببینیم چه خطایی هست
        print("❌ Error while processing update:", e)
        raise

    return "ok", 200

# -------------------------------
# اگر با python main.py اجرا شد (dev)، هم init کن
# -------------------------------
if __name__ == "__main__":
    ensure_initialized()
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
