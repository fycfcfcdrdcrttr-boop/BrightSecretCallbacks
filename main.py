import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

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

    site_time = time_tag.text.strip() if time_tag else ""

    return price_formatted, site_time


# -----------------------------
# ساخت منوی اصلی
# -----------------------------
def main_menu(first_name):
    keyboard = [
        [InlineKeyboardButton("💵 قیمت دلار", callback_data="dollar")],
        [InlineKeyboardButton("💰 قیمت طلا", callback_data="gold")],
        [InlineKeyboardButton("🪙 قیمت سکه", callback_data="coin")],
    ]
    return (
        f"سلام {first_name} جان 👋\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        InlineKeyboardMarkup(keyboard)
    )


# -----------------------------
# start
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text, keyboard = main_menu(user.first_name)
    await update.message.reply_text(text, reply_markup=keyboard)


# -----------------------------
# دکمه‌ها
# -----------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    urls = {
        "dollar": "https://www.tgju.org/profile/price_dollar_rl",
        "gold": "https://www.tgju.org/profile/geram18",
        "coin": "https://www.tgju.org/profile/sekee"
    }

    # اگر بازگشت بود
    if query.data == "back":
        user = query.from_user
        text, keyboard = main_menu(user.first_name)
        await query.edit_message_text(text, reply_markup=keyboard)
        return

    # اگر قیمت انتخاب شد
    price, site_time = fetch_price(urls[query.data])

    names = {
        "dollar": "💵 دلار",
        "gold": "💰 طلا ۱۸ عیار",
        "coin": "🪙 سکه"
    }

    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
    ]

    await query.edit_message_text(
        f"{names[query.data]}\n\n"
        f"قیمت: {price} تومان\n\n"
        f"🕒 زمان سایت:\n{site_time}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# -----------------------------
# اجرا
# -----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    app.run_polling()
