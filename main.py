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

# صف ارسال پیام‌ها برای جلوگیری از اشباع
message_queue = asyncio.Queue()

# -------------------------------
# کارگر برای ارسال پیام‌ها (به صورت ترتیبی)
# -------------------------------
async def message_worker():
    """در پس‌زمینه اجرا می‌شود و پیام‌ها را به‌ترتیب می‌فرستد."""
    while True:
        chat_id, text = await message_queue.get()
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            print("⚠️ send_message error:", e)
        message_queue.task_done()

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
    """پردازش پیام کاربر"""
    try:
        if update.message:
            text = update.message.text or ""
            chat_id = update.message.chat.id

            if text.startswith("/start"):
                await message_queue.put((chat_id, "سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس."))
            else:
                reply = await ask_openai(text)
                await message_queue.put((chat_id, reply))
    except Exception as e:
        print("❌ handle_update error:", e)

# -------------------------------
# Flask App (Webhook)
# -------------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Bot is running ... 1404/07/15 10:00 AM", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data:
            return "No data", 400
        update = Update.de_json(data, bot)
        # ارسال به background task queue
        asyncio.get_event_loop().create_task(handle_update(update))
        return jsonify({"status": "ok"})
    except Exception as e:
        print("❌ Webhook error:", e)
        return jsonify({"error": str(e)}), 500

# -------------------------------
# راه‌اندازی کامل
# -------------------------------
async def startup():
    print("⚙️ تنظیم webhook و راه‌اندازی بات...")
    try:
        await bot.delete_webhook()
        await bot.set_webhook(url=WEBHOOK_URL)
        print("🚀 Webhook set to:", WEBHOOK_URL)
    except Exception as e:
        print("⚠️ set_webhook failed:", e)
    # راه‌اندازی کارگر صف ارسال پیام
    asyncio.create_task(message_worker())

# -------------------------------
# اجرای محلی / Render
# -------------------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(startup())
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
