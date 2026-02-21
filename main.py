import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"


def get_dollar_price():
    url = "https://open.er-api.com/v6/latest/USD"
    response = requests.get(url)
    data = response.json()
    rate = data["rates"]["IRR"]
    toman = rate / 10
    return f"💵 قیمت دلار:\n{int(toman):,} تومان"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋\nبرای دریافت قیمت دلار دستور /dollar رو بزن")

async def dollar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = get_dollar_price()
    await update.message.reply_text(price)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dollar", dollar))

print("Bot running...")
app.run_polling()