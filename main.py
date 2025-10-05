import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Bot, Update
from openai import OpenAI

# -------------------------------
# تنظیمات
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE")  # مثال: "https://telegram-javidaibot.onrender.com"

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("کلیدهای TELEGRAM_TOKEN و OPENAI_API_KEY باید ست شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/{TELEGRAM_TOKEN}" if WEBHOOK_BASE else None

# -------------------------------
# کلاینت‌ها
# -------------------------------
bot = Bot(token=TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-3.5-turbo"

async def ask_openai(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        if resp.choices:
            choice = resp.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                return choice.message.content
            if hasattr(choice, "text"):
                return choice.text
        return str(resp)
    except Exception as e:
        return f"⚠️ خطا در ارتباط با OpenAI: {e}"

# -------------------------------
# Flask App (Webhook)
# -------------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Bot is running", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    if not data:
        return "No data", 400

    update = Update.de_json(data, bot)
    asyncio.create_task(handle_update(update))
    return jsonify({"status": "ok"})

async def handle_update(update: Update):
    if update.message:
        text = update.message.text or ""
        if text.startswith("/start"):
            await bot.send_message(chat_id=update.message.chat.id, text="سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس.")
        else:
            reply = await ask_openai(text)
            await bot.send_message(chat_id=update.message.chat.id, text=reply)

# -------------------------------
# ست کردن Webhook
# -------------------------------
if WEBHOOK_BASE:
    try:
        asyncio.run(bot.delete_webhook())
        asyncio.run(bot.set_webhook(url=WEBHOOK_URL))
        print("🚀 Webhook set to:", WEBHOOK_URL)
    except Exception as e:
        print("⚠️ set_webhook failed:", e)

# -------------------------------
# Run محلی (اختیاری)
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
