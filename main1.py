import os
import asyncio
import threading
from queue import SimpleQueue
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI



# -------------------------------
# Flask app
# -------------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "🤖 Bot is running!", 200

@flask_app.route("/python-version")
def python_version():
    import sys
    return f"Python version: {sys.version}", 200



# -------------------------------
# اجرای Flask
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
