import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"

# -----------------------------
# گرفتن قیمت از tgju
# -----------------------------
def get_market_prices():
    headers = {"User-Agent": "Mozilla/5.0"}

    urls = {
        "dollar": "https://www.tgju.org/profile/price_dollar_rl",
        "gold": "https://www.tgju.org/profile/geram18",
        "coin": "https://www.tgju.org/profile/sekee"
    }

    results = {}
    site_time = ""

    for key, url in urls.items():
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        price_tag = soup.find("span", {"data-col": "info.last_trade.PDrCotVal"})
        time_tag = soup.find("span", {"data-col": "info.dt"})

        if price_tag:
            price_text = price_tag.text.strip().replace(",", "")
            price = int(price_text) // 10
            results[key] = f"{price:,}"
        else:
            results[key] = "خطا"

        if key == "dollar" and time_tag:
            site_time = time_tag.text.strip()

    return (
        "📊 قیمت‌های لحظه‌ای بازار\n\n"
        f"💵 دلار: {results['dollar']} تومان\n"
        f"💰 طلا ۱۸ عیار: {results['gold']} تومان\n"
        f"🪙 سکه: {results['coin']} تومان\n\n"
        f"🕒 زمان سایت:\n{site_time}"
    )

# -----------------------------
# دستورات
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "برای دریافت قیمت بازار دستور /dollar رو بزن"
    )

async def dollar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = get_market_prices()
    await update.message.reply_text(prices)

# -----------------------------
# اجرای ربات (Polling)
# -----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dollar", dollar))

if __name__ == "__main__":
    app.run_polling()
