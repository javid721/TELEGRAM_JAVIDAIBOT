import os
import logging
import asyncio
import requests
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application
from openai import OpenAI

# -------------------------------
# تنظیمات محیطی
# -------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE")  # مثال: "https://telegram-javidaibot.onrender.com"

if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not WEBHOOK_BASE:
    raise RuntimeError("❌ کلیدهای TELEGRAM_TOKEN، OPENAI_API_KEY و WEBHOOK_BASE باید ست شوند!")

WEBHOOK_URL = f"{WEBHOOK_BASE.rstrip('/')}/webhook/{TELEGRAM_TOKEN}"

# -------------------------------
# کلاینت‌ها
# -------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-3.5-turbo"

# -------------------------------
# تنظیم لاگ‌ها
# -------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# Flask App
# -------------------------------
app = Flask(__name__)

# ساخت اپلیکیشن تلگرام (async)
application = Application.builder().token(TELEGRAM_TOKEN).build()


async def ask_openai(prompt: str) -> str:
    """ارسال پیام به OpenAI و دریافت پاسخ"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"⚠️ خطا در ارتباط با OpenAI: {e}")
        return "⚠️ خطا در پاسخ از OpenAI. لطفاً بعداً دوباره تلاش کنید."


async def handle_update(update: Update, context):
    """پردازش پیام تلگرام"""
    if not update.message:
        return

    chat_id = update.message.chat.id
    text = update.message.text or ""

    try:
        if text.startswith("/start"):
            await update.message.reply_text("سلام 👋 من به OpenAI وصلم! هرچی خواستی بپرس 😊")
        else:
            reply = await ask_openai(text)
            await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"❌ handle_update error: {e}")
        await update.message.reply_text("⚠️ مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")


# ثبت هندلر
application.add_handler(application.message_handler()(handle_update))


@app.route("/")
def home():
    return "✅ Bot is running successfully on Render!", 200


@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    """دریافت آپدیت از تلگرام"""
    data = await request.get_json(force=True)
    await application.update_queue.put(Update.de_json(data, application.bot))
    return jsonify({"status": "ok"}), 200


async def set_webhook():
    """تنظیم Webhook"""
    try:
        await application.bot.delete_webhook()
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"🚀 Webhook set to: {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"⚠️ set_webhook error: {e}")


if __name__ == "__main__":
    asyncio.run(set_webhook())
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
