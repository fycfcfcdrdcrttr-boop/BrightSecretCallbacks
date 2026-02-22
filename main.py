import requests
from bs4 import BeautifulSoup
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)
from telegram.constants import ChatAction, ParseMode
from datetime import datetime, timedelta
import pytz
import json
import os
import re

TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"
ADMIN_ID = 295168185

MUTE_FILE = "muted_users.json"
LOCK_FILE = "group_locks.json"
USERS_FILE = "users.json"


# ==============================
# ابزار ذخیره
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
# ذخیره کاربران
# ==============================

def save_user(user):
    users = load_json(USERS_FILE)
    if str(user.id) not in users:
        users[str(user.id)] = {
            "name": user.first_name,
            "username": user.username
        }
        save_json(USERS_FILE, users)


# ==============================
# قیمت
# ==============================

def fetch_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    price_tag = soup.find("span", {"data-col": "info.last_trade.PDrCotVal"})
    if price_tag:
        price = int(price_tag.text.strip().replace(",", "")) // 10
        price_formatted = f"{price:,}"
    else:
        price_formatted = "خطا"

    iran_time = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%H:%M:%S")
    return f"💰 <b>{price_formatted}</b> تومان\n🕒 {iran_time}"


# ==============================
# /start
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    await update.message.reply_text("سلام 👋 ربات فعاله.")


# ==============================
# /users
# ==============================

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = load_json(USERS_FILE)
    if not users:
        await update.message.reply_text("کاربری ثبت نشده.")
        return

    msg = "📋 لیست کاربران:\n\n"
    for uid, data in users.items():
        msg += f"👤 {data['name']}\n🆔 {uid}\n━━━━━━━━━━━━━━\n"

    await update.message.reply_text(msg)


# ==============================
# هندل پیام‌ها
# ==============================

async def group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    msg = update.message
    text = msg.text.strip() if msg.text else ""
    user = update.effective_user
    chat = msg.chat

    if chat.type not in ["group", "supergroup"]:
        return

    save_user(user)
    member = await context.bot.get_chat_member(chat.id, user.id)

    # ==============================
    # مدیریت قفل‌ها
    # ==============================

    locks = load_json(LOCK_FILE)
    gid = str(chat.id)

    if gid not in locks:
        locks[gid] = {
            "link": False,
            "photo": False,
            "voice": False,
            "forward": False,
            "only_admin": False
        }

    # تنظیم قفل توسط ادمین
    if member.status in ["administrator", "creator"]:

        lock_commands = {
            "قفل لینک": ("link", True),
            "باز لینک": ("link", False),
            "قفل عکس": ("photo", True),
            "باز عکس": ("photo", False),
            "قفل ویس": ("voice", True),
            "باز ویس": ("voice", False),
            "قفل فوروارد": ("forward", True),
            "باز فوروارد": ("forward", False),
            "فقط ادمین": ("only_admin", True),
            "باز همه": ("only_admin", False),
        }

        if text in lock_commands:
            key, value = lock_commands[text]
            locks[gid][key] = value
            save_json(LOCK_FILE, locks)
            await msg.reply_text("✅ تنظیم شد.")
            return

    # اجرای قفل برای کاربر عادی
    if member.status not in ["administrator", "creator"]:

        if locks[gid]["only_admin"]:
            await msg.delete()
            return

        if locks[gid]["link"] and text and re.search(r"http[s]?://|www\\.", text):
            await msg.delete()
            return

        if locks[gid]["photo"] and msg.photo:
            await msg.delete()
            return

        if locks[gid]["voice"] and msg.voice:
            await msg.delete()
            return

        if locks[gid]["forward"] and msg.forward_date:
            await msg.delete()
            return

    # ==============================
    # سکوت
    # ==============================

    muted = load_json(MUTE_FILE)

    if text.startswith("سکوت") and msg.reply_to_message:
        if member.status not in ["administrator", "creator"]:
            return

        target = msg.reply_to_message.from_user
        parts = text.split()

        if len(parts) == 2 and parts[1].isdigit():
            minutes = int(parts[1])
            until = datetime.now() + timedelta(minutes=minutes)

            await context.bot.restrict_chat_member(
                chat.id,
                target.id,
                ChatPermissions(can_send_messages=False),
                until_date=until
            )
        else:
            await context.bot.restrict_chat_member(
                chat.id,
                target.id,
                ChatPermissions(can_send_messages=False)
            )

        muted[str(target.id)] = target.first_name
        save_json(MUTE_FILE, muted)

        await msg.reply_text(f"🔇 {target.first_name} سکوت شد.")
        return

    # حذف سکوت
    if text == "حذف سکوت" and msg.reply_to_message:
        if member.status not in ["administrator", "creator"]:
            return

        target = msg.reply_to_message.from_user

        await context.bot.restrict_chat_member(
            chat.id,
            target.id,
            ChatPermissions(can_send_messages=True),
            until_date=None
        )

        muted.pop(str(target.id), None)
        save_json(MUTE_FILE, muted)

        await msg.reply_text(f"🔊 {target.first_name} آزاد شد.")
        return

    # ==============================
    # قیمت‌ها
    # ==============================

    prices = {
        "قیمت ارز": "https://www.tgju.org/profile/price_dollar_rl",
        "قیمت طلا": "https://www.tgju.org/profile/geram18",
        "قیمت سکه": "https://www.tgju.org/profile/sekee",
    }

    if text in prices:
        await msg.chat.send_action(ChatAction.TYPING)
        result = fetch_price(prices[text])
        await msg.reply_text(result, parse_mode=ParseMode.HTML)
        return

    # پاسخ ساده
    if text == "ربات":
        await msg.reply_text(f"جانم {user.first_name} 😊")


# ==============================
# اجرا
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("users", users_command))
app.add_handler(MessageHandler(filters.ALL, group_messages))

if __name__ == "__main__":
    app.run_polling()
