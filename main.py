import requests
from bs4 import BeautifulSoup
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction, ParseMode
from datetime import datetime, timedelta
import pytz
import asyncio
import json
import os
import pandas as pd

TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"


ADMIN_ID = 295168185
USERS_FILE = "users.json"


# ==============================
# مدیریت کاربران
# ==============================

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_user(user):
    users = load_users()

    if not any(u["user_id"] == user.id for u in users):
        users.append({
            "user_id": user.id,
            "first_name": user.first_name,
            "username": user.username if user.username else "ندارد",
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=4)


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
# منوی اصلی
# ==============================

def main_menu(first_name):
    keyboard = [
        [InlineKeyboardButton("💵 قیمت دلار", callback_data="dollar")],
        [InlineKeyboardButton("💰 قیمت طلا", callback_data="gold")],
        [InlineKeyboardButton("🪙 قیمت سکه", callback_data="coin")],
    ]

    text = f"سلام <b>{first_name}</b> جان 👋\n\nیکی از گزینه‌ها رو انتخاب کن:"

    return text, InlineKeyboardMarkup(keyboard)


# ==============================
# start
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    text, keyboard = main_menu(user.first_name)

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


# ==============================
# دکمه‌ها
# ==============================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back":
        text, keyboard = main_menu(query.from_user.first_name)
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

    selected = query.data.replace("refresh_", "")

    await query.message.chat.send_action(ChatAction.TYPING)
    await asyncio.sleep(1)

    price, site_time = fetch_price(urls[selected])
    message = build_price_message(names[selected], price, site_time)

    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"refresh_{selected}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
    ]

    await query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


# ==============================
# پیام‌های گروه (قیمت + سکوت)
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

    # ===== سکوت =====
    if text == "سکوت" and update.message.reply_to_message:

        member = await context.bot.get_chat_member(chat.id, user.id)

        if member.status not in ["administrator", "creator"]:
            await update.message.reply_text("❌ فقط ادمین میتونه سکوت کنه.")
            return

        target_user = update.message.reply_to_message.from_user
        mute_until = datetime.now() + timedelta(minutes=10)

        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=mute_until
        )

        await update.message.reply_text(
            f"🔇 {target_user.first_name} به مدت ۱۰ دقیقه سکوت شد."
        )
        return

    # ===== جواب ربات =====
    if text == "ربات":
        await update.message.reply_text(f"جانم {user.first_name} 😊")
        return

    urls = {
        "قیمت ارز": "https://www.tgju.org/profile/price_dollar_rl",
        "قیمت طلا": "https://www.tgju.org/profile/geram18",
        "قیمت سکه": "https://www.tgju.org/profile/sekee"
    }

    names = {
        "قیمت ارز": "💵 دلار",
        "قیمت طلا": "💰 طلا ۱۸ عیار",
        "قیمت سکه": "🪙 سکه"
    }

    if text in urls:
        await update.message.chat.send_action(ChatAction.TYPING)

        price, site_time = fetch_price(urls[text])
        message = build_price_message(names[text], price, site_time)

        await update.message.reply_text(
            message,
            parse_mode=ParseMode.HTML
        )


# ==============================
# اجرا
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_messages))

if __name__ == "__main__":
    app.run_polling()
