import os
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# «Ã«“Â «Ã—«Ì async loop œ— Colab
nest_asyncio.apply()

# -------------------------------
# ò·ÌœÂ«
# -------------------------------
try:
    from google.colab import userdata
    TELEGRAM_TOKEN = userdata.get("TELEGRAM_TOKEN_javidaibot")
    OPENAI_API_KEY = userdata.get("OPENAI_API_KEY")
except:
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("ò·ÌœÂ«Ì TELEGRAM_TOKEN Ê OPENAI_API_KEY »«Ìœ ”  ‘Ê‰œ!")

# -------------------------------
# « ’«· »Â OpenAI
# -------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"   # Ì« gpt-3.5-turbo »—«Ì „’—› ò„ —

def ask_openai(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"? Œÿ« œ— «— »«ÿ »« OpenAI: {e}"

# -------------------------------
# Â‰œ·—Â«Ì  ·ê—«„
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("”·«„ ?? „‰ »« OpenAI Ê’· ‘œ„! Â—çÌ ŒÊ«” Ì »Å—”.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    reply = await asyncio.to_thread(ask_openai, text)
    await update.message.reply_text(reply)

# -------------------------------
# ”«Œ  Application
# -------------------------------
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -------------------------------
# «Ã—«Ì polling œ— Colab/·Êò«·
# -------------------------------
print("?? —»«  œ— Õ«· «Ã—«” ... /start —« »“‰Ìœ.")
await application.run_polling()
