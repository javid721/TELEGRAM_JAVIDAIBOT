import os
import asyncio
from flask import Flask, request, abort
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE", "")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("کلیدهای TELEGRAM_TOKEN و OPENAI_API_KEY باید ست شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/{TELEGRAM_TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-3.5-turbo"

async def ask_openai(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            choice = resp.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                return choice.message.content
            if hasattr(choice, "text"):
                return choice.text
        return str(resp)
    except Exception as e:
        return f"⚠️ خطا در ارتباط با OpenAI: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    reply = await ask_openai(text)
    await update.message.reply_text(reply)

# -------------------------------
# ایجاد Application و اضافه کردن هندلرها
# -------------------------------
app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# -------------------------------
# Flask
# -------------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ Bot is running (webhook mode).", 200

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    if request.content_type != 'application/json':
        abort(400)
    data = request.get_json(force=True)
    if not data:
        abort(400)
    update = Update.de_json(data, app_bot.bot)
    try:
        asyncio.run(app_bot.process_update(update))
    except Exception as e:
        print("❌ Error processing update:", e)
    return "OK", 200

# -------------------------------
# set webhook
# -------------------------------
try:
    app_bot.bot.delete_webhook()
    if WEBHOOK_BASE:
        app_bot.bot.set_webhook(url=WEBHOOK_URL)
        print("🚀 Webhook set to:", WEBHOOK_URL)
    else:
        print("⚠️ WEBHOOK_BASE خالی است — webhook ست نشده.")
except Exception as e:
    print("⚠️ set_webhook failed:", e)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
