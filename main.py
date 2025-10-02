import os
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# ����� ����� async loop �� Colab
nest_asyncio.apply()

# -------------------------------
# ������
# -------------------------------
try:
    from google.colab import userdata
    TELEGRAM_TOKEN = userdata.get("TELEGRAM_TOKEN_javidaibot")
    OPENAI_API_KEY = userdata.get("OPENAI_API_KEY")
except:
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
# ���� Application
# -------------------------------
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -------------------------------
# ����� polling �� Colab/����
# -------------------------------
print("?? ���� �� ��� ������... /start �� �����.")
await application.run_polling()
