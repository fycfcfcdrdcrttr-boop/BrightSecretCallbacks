import requests
from bs4 import BeautifulSoup
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction, ParseMode
from datetime import datetime, timedelta
import pytz
import json
import os


TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"

MUTE_FILE = "muted_users.json"
STATS_FILE = "daily_stats.json"


# ==============================
# مدیریت فایل‌ها
# ==============================

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


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
    iran_time = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%H:%M:%S")
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
# پیام‌های گروه
# ==============================

async def group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text
    if not text:
        return

    text = text.strip()
    user = update.effective_user
    chat = update.message.chat

    if chat.type not in ["group", "supergroup"]:
        return

    # --------------------------
    # 📊 شمارش پیام‌های روزانه
    # --------------------------
    stats = load_json(STATS_FILE)
    today = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%Y-%m-%d")

    if today not in stats:
        stats = {today: 0}

    stats[today] += 1
    save_json(STATS_FILE, stats)

    member = await context.bot.get_chat_member(chat.id, user.id)
    muted_users = load_json(MUTE_FILE)

    # ======================
    # ⏳ سکوت زمان‌دار یا دائمی
    # ======================
    if text.startswith("سکوت") and update.message.reply_to_message:

        if member.status not in ["administrator", "creator"]:
            await update.message.reply_text("❌ فقط ادمین میتونه سکوت کنه.")
            return

        parts = text.split()
        target_user = update.message.reply_to_message.from_user

        if len(parts) == 2 and parts[1].isdigit():
            minutes = int(parts[1])
            until_time = datetime.now() + timedelta(minutes=minutes)

            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=target_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_time
            )

            await update.message.reply_text(
                f"🔇 {target_user.first_name} به مدت {minutes} دقیقه سکوت شد."
            )

        else:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=target_user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )

            await update.message.reply_text(
                f"🔇 {target_user.first_name} تا اطلاع ثانوی سکوت شد."
            )

        muted_users[str(target_user.id)] = target_user.first_name
        save_json(MUTE_FILE, muted_users)
        return

    # ======================
    # حذف سکوت
    # ======================
    if text == "حذف سکوت" and update.message.reply_to_message:

        if member.status not in ["administrator", "creator"]:
            await update.message.reply_text("❌ فقط ادمین میتونه حذف سکوت کنه.")
            return

        target_user = update.message.reply_to_message.from_user

        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=True),
            until_date=None
        )

        muted_users.pop(str(target_user.id), None)
        save_json(MUTE_FILE, muted_users)

        await update.message.reply_text(
            f"🔊 {target_user.first_name} از حالت سکوت خارج شد."
        )
        return

    # ======================
    # 📊 آمار امروز
    # ======================
    if text == "آمار امروز":
        count = stats.get(today, 0)
        await update.message.reply_text(
            f"📊 تعداد پیام‌های امروز گروه:\n\n{count} پیام"
        )
        return

    # ======================
    # پاسخ ساده
    # ======================
    if text == "ربات":
        await update.message.reply_text(f"جانم {user.first_name} 😊")
        return

    # ======================
    # قیمت‌ها
    # ======================
    urls = {
        "قیمت ارز": ("💵 دلار", "https://www.tgju.org/profile/price_dollar_rl"),
        "قیمت طلا": ("💰 طلا ۱۸ عیار", "https://www.tgju.org/profile/geram18"),
        "قیمت سکه": ("🪙 سکه", "https://www.tgju.org/profile/sekee")
    }

    if text in urls:
        await update.message.chat.send_action(ChatAction.TYPING)

        name, url = urls[text]
        price, site_time = fetch_price(url)
        message = build_price_message(name, price, site_time)

        await update.message.reply_text(
            message,
            parse_mode=ParseMode.HTML
        )


# ==============================
# اجرا
# ==============================

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_messages))

if __name__ == "__main__":
    app.run_polling()
