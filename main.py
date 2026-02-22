import requests
from bs4 import BeautifulSoup
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from telegram.constants import ChatAction
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

    # --------------------------
    # 📊 ثبت آمار پیام
    # --------------------------
    stats = load_json(STATS_FILE)
    today = datetime.now(pytz.timezone("Asia/Tehran")).strftime("%Y-%m-%d")

    if today not in stats:
        stats[today] = {
            "users": {},
            "total": 0
        }

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
    # 📊 آمار امروز
    # ======================
    if text == "آمار امروز":

        if member.status not in ["administrator", "creator"]:
            return

        if today not in stats:
            await update.message.reply_text("امروز پیامی ثبت نشده.")
            return

        msg = "📊 آمار پیام‌های امروز:\n\n"

        for uid, data in stats[today]["users"].items():
            msg += (
                f"👤 {data['name']}\n"
                f"🆔 {uid}\n"
                f"💬 {data['count']} پیام\n"
                f"━━━━━━━━━━━━━━\n"
            )

        msg += f"\n📈 مجموع کل پیام‌های امروز گروه:\n{stats[today]['total']} پیام"

        await update.message.reply_text(msg)
        return

    # ======================
    # سکوت
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
    # حذف سکوت
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
    # لیست سکوت
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
    # پاسخ ساده
    # ======================
    if text == "ربات":
        await update.message.reply_text(f"جانم {user.first_name} 😊")
        return


# ==============================
# اجرا
# ==============================

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_messages))

if __name__ == "__main__":
    app.run_polling()
