import os
import asyncio
import requests
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio

nest_asyncio.apply()

# -------------------------------
# œ—Ì«›   Êò‰ùÂ«
# -------------------------------
try:
    # Õ«·  Colab
    from google.colab import userdata
    TELEGRAM_TOKEN = userdata.get('TELEGRAM_TOKEN_javidaibot')
    OPENROUTER_API_KEY = userdata.get("OPENROUTER_API_KEY")
except:
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    raise RuntimeError("ò·ÌœÂ«Ì TELEGRAM_TOKEN Ê OPENROUTER_API_KEY »«Ìœ ”  ‘Ê‰œ!")

# «ê— —ÊÌ ”—Ê— Â” Ì„ »—«Ì Ê»ÂÊò ÌÂ „”Ì— „Õ—„«‰Â ”  ò‰
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", TELEGRAM_TOKEN)
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-r1:free"

# -------------------------------
# OpenRouter
# -------------------------------
def ask_openrouter(prompt: str) -> str:
    resp = requests.post(
        BASE_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": MODEL, "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# -------------------------------
# Telegram App
# -------------------------------
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("”·«„ ?? „‰ —»«  ¬„«œÂ »Â ò«— Â” „!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    reply = await asyncio.to_thread(ask_openrouter, text)
    await update.message.reply_text(reply)

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -------------------------------
# FastAPI + lifespan (»—«Ì ”—Ê—)
# -------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.start()
    yield
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook/{path}")
async def webhook(path: str, request: Request):
    if path != WEBHOOK_PATH:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

# -------------------------------
# Õ«·   ” Ì (Polling) ? Colab/·Êò«·
# -------------------------------
if __name__ == "__main__":
    print("?? —»«  œ— Õ«·  polling «Ã—« ‘œ! œ—  ·ê—«„ ÅÌ«„ »œÂ...")
    telegram_app.run_polling(close_loop=False)
