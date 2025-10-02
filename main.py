import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# -------------------------------
# ò·ÌœÂ«
# -------------------------------
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
# ”«Œ  «Å·ÌòÌ‘‰  ·ê—«„
# -------------------------------
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -------------------------------
# ”«Œ  Flask »—«Ì Ê»ÂÊò
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
# «Ã—«Ì »—‰«„Â
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
