import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
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
# Bot و Dispatcher
# -------------------------------
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# -------------------------------
# Handlers
def start(update, context):
    update.message.reply_text("سلام  من به OpenAI وصلم! هرچی خواستی بپرس.")

def handle_message(update, context):
    text = update.message.text or ""
    reply = ask_openai(text)
    update.message.reply_text(reply)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# -------------------------------
# Flask
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "سلام Bot is running!", 200

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)  # sync
    return "ok", 200

# -------------------------------
# Set webhook
bot.delete_webhook()
bot.set_webhook(url=WEBHOOK_URL)
print(" Webhook set to", WEBHOOK_URL)

# -------------------------------
# اجرای Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
