import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# -------------------------------
# ������
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("������� TELEGRAM_TOKEN � OPENAI_API_KEY ���� �� ����!")

# -------------------------------
# ����� �� OpenAI
# -------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"   # �� gpt-3.5-turbo ���� ���� ����

def ask_openai(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"? ��� �� ������ �� OpenAI: {e}"

# -------------------------------
# �������� �����
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("���� ?? �� �� OpenAI ��� ���! �э� ������ ȁ��.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    reply = await asyncio.to_thread(ask_openai, text)
    await update.message.reply_text(reply)

# -------------------------------
# ���� ǁ����� �����
# -------------------------------
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -------------------------------
# ���� Flask ���� ����
# -------------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "?? Bot is running!", 200

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok", 200

# -------------------------------
# ����� ������
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
