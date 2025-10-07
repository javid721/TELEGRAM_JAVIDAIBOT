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

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/webhook/{TELEGRAM_TOKEN}" if WEBHOOK_BASE else None

# -------------------------------
# کلاینت‌ها
# -------------------------------
bot = Bot(token=TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-3.5-turbo"

# -------------------------------
# توابع کمکی
# -------------------------------
async def ask_openai(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ خطا در ارتباط با OpenAI: {e}"

async def handle_update(update: Update):
    try:
        if update.message:
            text = update.message.text or ""
            chat_id = update.message.chat.id

            if text.startswith("/start"):
                await bot.send_message(
                    chat_id=chat_id,
                    text="سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس."
                )
            else:
                reply = await ask_openai(text)
                await bot.send_message(chat_id=chat_id, text=reply)
    except Exception as e:
        print("❌ handle_update error:", e)

# -------------------------------
# Flask App (Webhook)
# -------------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Bot is running ... 1404/07/15 09:45 AM", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """دریافت آپدیت از تلگرام و اجرای امن async"""
    try:
        data = request.get_json(force=True)
        if not data:
            return "No data", 400

        update = Update.de_json(data, bot)
        asyncio.run(handle_update(update))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("❌ Webhook error:", e)
        return jsonify({"error": str(e)}), 500

# -------------------------------
# ست کردن Webhook
# -------------------------------
if WEBHOOK_BASE:
    try:
        print("⚙️ تنظیم webhook...")
        asyncio.run(bot.delete_webhook())
        asyncio.run(bot.set_webhook(url=WEBHOOK_URL))
        print("🚀 Webhook set to:", WEBHOOK_URL)
    except Exception as e:
        print("⚠️ set_webhook failed:", e)

# -------------------------------
# اجرای محلی (اختیاری)
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
