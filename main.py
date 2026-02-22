import requests
from bs4 import BeautifulSoup
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.constants import ChatAction, ParseMode
from datetime import datetime
import pytz
import asyncio
import json
import os
import pandas as pd

TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"
ADMIN_ID = 295168185


USERS_FILE = "users.json"


# ==============================
# مدیریت کاربران
# ==============================

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_user(user):
    users = load_users()

    if not any(u["user_id"] == user.id for u in users):
        users.append({
            "user_id": user.id,
            "first_name": user.first_name,
            "username": user.username if user.username else "ندارد",
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=4)


# ==============================
# start
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    await update.message.reply_text(
        f"سلام {user.first_name} جان 👋"
    )


# ==============================
# لیست کاربران
# ==============================

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = load_users()

    if not users:
        await update.message.reply_text("هیچ کاربری ثبت نشده.")
        return

    text = "📋 لیست کاربران:\n\n"

    for u in users:
        text += (
            f"👤 {u['first_name']} | @{u['username']}\n"
            f"🆔 {u['user_id']}\n"
            f"📅 {u['joined_at']}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(text)


# ==============================
# خروجی اکسل
# ==============================

async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = load_users()

    if not users:
        await update.message.reply_text("هیچ کاربری برای خروجی وجود ندارد.")
        return

    df = pd.DataFrame(users)

    file_name = "users_export.xlsx"
    df.to_excel(file_name, index=False)

    await update.message.reply_document(
        document=open(file_name, "rb"),
        filename=file_name,
        caption="📊 خروجی کاربران"
    )


# ==============================
# اجرا
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("users", users))
app.add_handler(CommandHandler("export", export_users))

if __name__ == "__main__":
    app.run_polling()
