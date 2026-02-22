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

TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"


# -----------------------------
# گرفتن قیمت
# -----------------------------
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


# -----------------------------
# منوی اصلی
# -----------------------------
def main_menu(first_name):
    keyboard = [
        [InlineKeyboardButton("💵 قیمت دلار", callback_data="dollar")],
        [InlineKeyboardButton("💰 قیمت طلا", callback_data="gold")],
        [InlineKeyboardButton("🪙 قیمت سکه", callback_data="coin")],
    ]

    text = (
        f"سلام <b>{first_name}</b> جان 👋\n\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:"
    )

    return text, InlineKeyboardMarkup(keyboard)


# -----------------------------
# ساخت پیام قیمت
# -----------------------------
def build_price_message(name, price, site_time):
    iran_tz = pytz.timezone("Asia/Tehran")
    iran_time = datetime.now(iran_tz).strftime("%H:%M:%S")

    message = (
        f"━━━━━━━━━━━━━━━\n"
        f"<b>{name}</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💰 قیمت: <b>{price}</b> تومان\n\n"
        f"🕒 زمان سایت: {site_time}\n"
        f"🇮🇷 ساعت ایران: {iran_time}\n"
        f"━━━━━━━━━━━━━━━"
    )

    return message


# -----------------------------
# /start
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text, keyboard = main_menu(user.first_name)

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


# -----------------------------
# مدیریت دکمه‌ها
# -----------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    # بازگشت به منو
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

    # اگر بروزرسانی بود
    if query.data.startswith("refresh_"):
        selected = query.data.replace("refresh_", "")
    else:
        selected = query.data

    # تایپینگ
    await query.message.chat.send_action(ChatAction.TYPING)
    await asyncio.sleep(1)

    price, site_time = fetch_price(urls[selected])
    message = build_price_message(names[selected], price, site_time)

    # دکمه‌ها
    keyboard = [
        [
            InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"refresh_{selected}")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back")
        ]
    ]

    await query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


# -----------------------------
# اجرای ربات
# -----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    app.run_polling()
