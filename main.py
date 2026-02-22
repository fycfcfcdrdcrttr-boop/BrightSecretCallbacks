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
from datetime import datetime
import pytz
import json
import os


TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"
MUTE_FILE = "muted_users.json"


# ==============================
# مدیریت لیست سکوت
# ==============================

def load_muted():
    if not os.path.exists(MUTE_FILE):
        return {}
    with open(MUTE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_muted(data):
    with open(MUTE_FILE, "w", encoding="utf-8") as f:
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

    member = await context.bot.get_chat_member(chat.id, user.id)
    muted_users = load_muted()

    # ======================
    # سکوت
    # ======================
    if text == "سکوت" and update.message.reply_to_message:

        if member.status not in ["administrator", "creator"]:
            await update.message.reply_text("❌ فقط ادمین میتونه سکوت کنه.")
            return

        target_user = update.message.reply_to_message.from_user

        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )

        # ذخیره در لیست
        muted_users[str(target_user.id)] = target_user.first_name
        save_muted(muted_users)

        await update.message.reply_text(
            f"🔇 {target_user.first_name} تا اطلاع ثانوی سکوت شد."
        )
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

        # حذف از لیست
        muted_users.pop(str(target_user.id), None)
        save_muted(muted_users)

        await update.message.reply_text(
            f"🔊 کاربر {target_user.first_name} از حالت سکوت خارج شد."
        )
        return

    # ======================
    # لیست سکوت
    # ======================
    if text == "لیست سکوت":

        if member.status not in ["administrator", "creator"]:
            return

        if not muted_users:
            await update.message.reply_text("📋 هیچ کاربری در حالت سکوت نیست.")
            return

        msg = "📋 لیست افراد سکوت‌شده:\n\n"
        for name in muted_users.values():
            msg += f"• {name}\n"

        await update.message.reply_text(msg)
        return

    # ======================
    # جواب ساده
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
