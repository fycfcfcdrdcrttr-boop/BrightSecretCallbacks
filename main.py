from flask import Flask
from threading import Thread

app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "Bot is alive"

def run():
    app_web.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()



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

TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"


# -----------------------------
# گرفتن قیمت از tgju
# -----------------------------
def get_market_prices():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

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
            price = int(price_text)

            # دلار ریال هست → تبدیل به تومان
            price = price // 10

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
        f"🕒 زمان بروزرسانی سایت:\n{site_time}"
    )


# -----------------------------
# /start
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n\n"
        "دستور‌ها:\n"
        "/dollar → دریافت قیمت بازار\n"
        "/auto → فعال‌سازی ارسال خودکار هر ۵ دقیقه\n"
        "/stop → توقف ارسال خودکار"
    )


# -----------------------------
# /dollar
# -----------------------------
async def dollar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = get_market_prices()

    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(prices, reply_markup=reply_markup)


# -----------------------------
# دکمه بروزرسانی
# -----------------------------
async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    new_text = get_market_prices()

    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # فقط اگر تغییر کرده ادیت کن
    if query.message.text != new_text:
        await query.edit_message_text(new_text, reply_markup=reply_markup)


# -----------------------------
# ارسال خودکار
# -----------------------------
async def auto_send(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    prices = get_market_prices()
    await context.bot.send_message(chat_id=chat_id, text=prices)


async def auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    context.job_queue.run_repeating(
        auto_send,
        interval=300,  # هر 5 دقیقه
        first=0,
        chat_id=chat_id,
        name=str(chat_id)
    )

    await update.message.reply_text("⏱ ارسال خودکار هر ۵ دقیقه فعال شد.")


# -----------------------------
# توقف ارسال خودکار
# -----------------------------
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    current_jobs = context.job_queue.get_jobs_by_name(chat_id)

    if not current_jobs:
        await update.message.reply_text("ارسال خودکار فعال نیست.")
        return

    for job in current_jobs:
        job.schedule_removal()

    await update.message.reply_text("⛔ ارسال خودکار متوقف شد.")


# -----------------------------
# ساخت اپ
# -----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dollar", dollar))
app.add_handler(CommandHandler("auto", auto))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CallbackQueryHandler(refresh, pattern="refresh"))

print("Bot running...")
keep_alive()
app.run_polling()




