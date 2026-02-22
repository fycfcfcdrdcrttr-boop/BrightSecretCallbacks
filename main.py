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
# گرفتن قیمت
# ==============================

def fetch_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    price_tag = soup.find("span", {"data-col": "info.last_trade.PDrCotVal"})
    time_tag = soup.find("span", {"data-col": "info.dt"})

    if price_tag:
        price_text = price_tag.text.strip().replace(",", "")
        price = int(price_text) // 10
        price_formatted = f"{price:,}"
    else:
        price_formatted = "خطا"

    site_time = time_tag.text.strip() if time_tag else "نامشخص"

    return price_formatted, site_time


def build_price_message(name, price, site_time):
    iran_tz = pytz.timezone("Asia/Tehran")
    iran_time = datetime.now(iran_tz).strftime("%H:%M:%S")

    return (
        f"━━━━━━━━━━━━━━━\n"
        f"<b>{name}</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💰 قیمت: <b>{price}</b> تومان\n\n"
        f"🕒 زمان سایت: {site_time}\n"
        f"🇮🇷 ساعت ایران: {iran_time}\n"
        f"━━━━━━━━━━━━━━━"
    )


# ==============================
# منوی اصلی
# ==============================

def main_menu(first_name):
    keyboard = [
        [InlineKeyboardButton("💵 قیمت دلار", callback_data="dollar")],
        [InlineKeyboardButton("💰 قیمت طلا", callback_data="gold")],
        [InlineKeyboardButton("🪙 قیمت سکه", callback_data="coin")],
    ]

    text = (
        f"سلام <b>{first_name}</b> جان 👋\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:"
    )

    return text, InlineKeyboardMarkup(keyboard)


# ==============================
# start
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    text, keyboard = main_menu(user.first_name)

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


# ==============================
# دکمه‌ها
# ==============================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    if query.data == "back":
        text, keyboard = main_menu(user.first_name)
        await query.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return

    urls = {
        "dollar": "https://www.tgju.org/profile/price_dollar_rl",
        "gold": "https://www.tgju.org/profile/geram18",
        "coin": "https://www.tgju.org/profile/sekee"
    }

    names = {
        "dollar": "💵 دلار",
        "gold": "💰 طلا ۱۸ عیار",
        "coin": "🪙 سکه"
    }

    selected = query.data.replace("refresh_", "")

    await query.message.chat.send_action(ChatAction.TYPING)
    await asyncio.sleep(1)

    price, site_time = fetch_price(urls[selected])
    message = build_price_message(names[selected], price, site_time)

    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"refresh_{selected}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
    ]

    await query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


# ==============================
# دیدن لیست کاربران (ادمین)
# ==============================

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = load_users()

    if not users:
        await update.message.reply_text("هیچ کاربری ثبت نشده.")
        return

    message = "📋 لیست کاربران:\n\n"

    for u in users:
        message += (
            f"👤 نام: {u['first_name']}\n"
            f"🔹 یوزرنیم: @{u['username']}\n"
            f"🆔 آیدی: {u['user_id']}\n"
            f"📅 تاریخ عضویت: {u['joined_at']}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(message)


# ==============================
# تعداد کاربران (ادمین)
# ==============================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = load_users()
    await update.message.reply_text(f"📊 تعداد کاربران: {len(users)}")


# ==============================
# اجرا
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("users", users))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    app.run_polling()
