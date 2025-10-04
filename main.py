import os
import asyncio
import threading
from queue import SimpleQueue
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# -------------------------------
# کلیدها و تنظیمات
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE", "https://telegram-javidaibot.onrender.com")

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
        return f" خطا در ارتباط با OpenAI: {e}"

# -------------------------------
# هندلرهای تلگرام
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام  من به OpenAI وصلم! هرچی خواستی بپرس.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    reply = await asyncio.to_thread(ask_openai, text)
    await update.message.reply_text(reply)

# -------------------------------
# اپلیکیشن تلگرام
# -------------------------------
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -------------------------------
# Queue برای وبهوک
# -------------------------------
update_queue = SimpleQueue()

# -------------------------------
# Background thread برای پردازش updateها
# -------------------------------
def process_updates():
    while True:
        data = update_queue.get()
        if data:
            update = Update.de_json(data, application.bot)
            try:
                asyncio.run(application.process_update(update))
            except Exception as e:
                print(" Error processing update:", e)

threading.Thread(target=process_updates, daemon=True).start()

# -------------------------------
# Flask app
# -------------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "🤖 Bot is running!", 200

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update_queue.put(data)
    return "ok", 200  # پاسخ سریع به تلگرام

# -------------------------------
# Initialize و set webhook
# -------------------------------
async def init_application():
    await application.initialize()
    await application.start()
    try:
        await application.bot.delete_webhook()
    except Exception as e:
        print(" delete_webhook failed:", e)
    try:
        await application.bot.set_webhook(url=WEBHOOK_URL)
        print(" Webhook set to", WEBHOOK_URL)
    except Exception as e:
        print(" set_webhook failed:", e)

asyncio.run(init_application())

# -------------------------------
# اجرای Flask
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
