import requests
from bs4 import BeautifulSoup
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from telegram.constants import ChatAction, ParseMode
from datetime import datetime, timedelta
import pytz
import json
import os
import re


TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"

MUTE_FILE = "muted_users.json"
STATS_FILE = "daily_stats.json"


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

    iran_time = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%H:%M:%S")

    return (
        f"━━━━━━━━━━━━━━━\n"
        f"<b>💰 قیمت لحظه‌ای</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💵 قیمت: <b>{price_formatted}</b> تومان\n\n"
        f"🕒 زمان سایت: {site_time}\n"
        f"🇮🇷 ساعت ایران: {iran_time}\n"
        f"━━━━━━━━━━━━━━━"
    )


# ==============================
# هندل پیام‌ها
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



     # --------------------------
    # مدیریت قفل‌ها
    # --------------------------

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

    # فقط ادمین اجازه تنظیم قفل
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

    # اگر کاربر عادی است
    if member.status not in ["administrator", "creator"]:

        # حالت فقط ادمین
        if locks[gid]["only_admin"]:
            await msg.delete()
            return

        # قفل لینک
        if locks[gid]["link"] and text:
            if re.search(r"http[s]?://|www\\.", text):
                await msg.delete()
                return

        # قفل عکس
        if locks[gid]["photo"] and msg.photo:
            await msg.delete()
            return

        # قفل ویس
        if locks[gid]["voice"] and msg.voice:
            await msg.delete()
            return

        # قفل فوروارد
        if locks[gid]["forward"] and msg.forward_date:
            await msg.delete()
            return




    # --------------------------
    # 📊 ثبت آمار پیام
    # --------------------------
    stats = load_json(STATS_FILE)
    today = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%Y-%m-%d")

    if today not in stats:
        stats[today] = {"users": {}, "total": 0}

    uid = str(user.id)

    if uid not in stats[today]["users"]:
        stats[today]["users"][uid] = {
            "name": user.first_name,
            "count": 0
        }

    stats[today]["users"][uid]["count"] += 1
    stats[today]["total"] += 1

    save_json(STATS_FILE, stats)

    muted_users = load_json(MUTE_FILE)

    # ======================
    # 💰 قیمت‌ها
    # ======================
    prices = {
        "قیمت ارز": "https://www.tgju.org/profile/price_dollar_rl",
        "قیمت طلا": "https://www.tgju.org/profile/geram18",
        "قیمت سکه": "https://www.tgju.org/profile/sekee",
    }

    if text in prices:
        await update.message.chat.send_action(ChatAction.TYPING)
        msg = fetch_price(prices[text])
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # ======================
    # 📊 آمار امروز
    # ======================
    if text == "آمار امروز":

        if member.status not in ["administrator", "creator"]:
            return

        msg = "📊 آمار پیام‌های امروز:\n\n"

        for uid, data in stats[today]["users"].items():
            msg += (
                f"👤 {data['name']}\n"
                f"🆔 {uid}\n"
                f"💬 {data['count']} پیام\n"
                f"━━━━━━━━━━━━━━\n"
            )

        msg += f"\n📈 مجموع کل پیام‌های امروز:\n{stats[today]['total']} پیام"

        await update.message.reply_text(msg)
        return

    # ======================
    # 🔇 سکوت
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
                chat.id,
                target_user.id,
                ChatPermissions(can_send_messages=False),
                until_date=until_time
            )

            await update.message.reply_text(
                f"🔇 {target_user.first_name} به مدت {minutes} دقیقه سکوت شد."
            )
        else:
            await context.bot.restrict_chat_member(
                chat.id,
                target_user.id,
                ChatPermissions(can_send_messages=False)
            )

            await update.message.reply_text(
                f"🔇 {target_user.first_name} تا اطلاع ثانوی سکوت شد."
            )

        muted_users[str(target_user.id)] = target_user.first_name
        save_json(MUTE_FILE, muted_users)
        return

    # ======================
    # 🔊 حذف سکوت
    # ======================
    if text == "حذف سکوت" and update.message.reply_to_message:

        if member.status not in ["administrator", "creator"]:
            return

        target_user = update.message.reply_to_message.from_user

        await context.bot.restrict_chat_member(
            chat.id,
            target_user.id,
            ChatPermissions(can_send_messages=True),
            until_date=None
        )

        muted_users.pop(str(target_user.id), None)
        save_json(MUTE_FILE, muted_users)

        await update.message.reply_text(
            f"🔊 {target_user.first_name} از حالت سکوت خارج شد."
        )
        return

    # ======================
    # 📋 لیست سکوت
    # ======================
    if text == "لیست سکوت":

        if member.status not in ["administrator", "creator"]:
            return

        if not muted_users:
            await update.message.reply_text("📋 هیچ کاربری در حالت سکوت نیست.")
            return

        msg = "📋 لیست افراد سکوت‌شده:\n\n"

        for uid, name in muted_users.items():
            msg += f"👤 {name}\n🆔 {uid}\n━━━━━━━━━━━━━━\n"

        await update.message.reply_text(msg)
        return

    # ======================
    # 🤖 پاسخ ساده
    # ======================
    if text == "ربات":
        await update.message.reply_text(f"جانم {user.first_name} 😊")
        return


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_messages))

if __name__ == "__main__":
    app.run_polling()
