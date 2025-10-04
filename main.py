import os
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from openai import OpenAI

# -------------------------------
# کلیدها و تنظیمات
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("کلیدهای TELEGRAM_TOKEN و OPENAI_API_KEY باید ست شوند!")

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
# Handlers
def start(update, context):
    update.message.reply_text("سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس.")

def handle_message(update, context):
    text = update.message.text or ""
    reply = ask_openai(text)
    update.message.reply_text(reply)

# -------------------------------
# Updater و Dispatcher (long polling)
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# -------------------------------
# اجرای bot
if __name__ == "__main__":
    print("🤖 Bot is running with long polling...")
    updater.start_polling()
    updater.idle()
