import requests
from bs4 import BeautifulSoup
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ChatAction, ParseMode
from datetime import datetime, timedelta
import pytz
import json
import os
import re
import random

TOKEN = "8479810920:AAH6avKRGiXdv6cKb-fNGMlxMfYREv74Q3E"
ADMIN_ID = 295168185

MUTE_FILE = "muted_users.json"
LOCK_FILE = "group_locks.json"
USERS_FILE = "users.json"
RPS_FILE = "rps_stats.json"
HOKM_FILE = "hokm_games.json"


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
# مدیریت آمار بازی
# ==============================

def update_rps_stats(user_id, name, result):
    stats = load_json(RPS_FILE)

    if str(user_id) not in stats:
        stats[str(user_id)] = {
            "name": name,
            "win": 0,
            "lose": 0,
            "draw": 0,
            "score": 0
        }

    if result == "win":
        stats[str(user_id)]["win"] += 1
        stats[str(user_id)]["score"] += 3
    elif result == "lose":
        stats[str(user_id)]["lose"] += 1
    elif result == "draw":
        stats[str(user_id)]["draw"] += 1
        stats[str(user_id)]["score"] += 1

    save_json(RPS_FILE, stats)


# ==============================
# بازی سنگ کاغذ قیچی
# ==============================

def rps_menu():
    keyboard = [[
        InlineKeyboardButton("✊ سنگ", callback_data="rps_rock"),
        InlineKeyboardButton("✋ کاغذ", callback_data="rps_paper"),
        InlineKeyboardButton("✌ قیچی", callback_data="rps_scissors"),
    ]]
    return InlineKeyboardMarkup(keyboard)


async def rps_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_choice = query.data.split("_")[1]
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)

    emoji = {
        "rock": "✊ سنگ",
        "paper": "✋ کاغذ",
        "scissors": "✌ قیچی"
    }

    if user_choice == bot_choice:
        result_text = "🤝 مساوی شد!"
        update_rps_stats(user.id, user.first_name, "draw")

    elif (
        (user_choice == "rock" and bot_choice == "scissors") or
        (user_choice == "paper" and bot_choice == "rock") or
        (user_choice == "scissors" and bot_choice == "paper")
    ):
        result_text = "🎉 تو بردی!"
        update_rps_stats(user.id, user.first_name, "win")

    else:
        result_text = "😎 من بردم!"
        update_rps_stats(user.id, user.first_name, "lose")

    text = (
        f"👤 انتخاب تو: {emoji[user_choice]}\n"
        f"🤖 انتخاب من: {emoji[bot_choice]}\n\n"
        f"{result_text}"
    )

    await query.edit_message_text(text)


# ==============================
# بازی حکم
# ==============================

SUITS = {"♠️": "پیک", "♥️": "دل", "♦️": "خشت", "♣️": "گشنیز"}
SUIT_EMOJIS = list(SUITS.keys())
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
RANK_VALUES = {r: i for i, r in enumerate(RANKS)}

def make_deck():
    deck = []
    for suit in SUIT_EMOJIS:
        for rank in RANKS:
            deck.append(f"{rank}{suit}")
    random.shuffle(deck)
    return deck

def get_card_rank(card):
    return card[:-2] if card[:-2] in RANKS else card[0]

def get_card_suit(card):
    return card[-2:]

def hokm_join_keyboard(chat_id):
    keyboard = [[InlineKeyboardButton("🃏 پیوستن به بازی", callback_data=f"hokm_join_{chat_id}")]]
    return InlineKeyboardMarkup(keyboard)

def hokm_suit_keyboard(chat_id):
    keyboard = [[
        InlineKeyboardButton("♠️ پیک", callback_data=f"hokm_suit_{chat_id}_♠️"),
        InlineKeyboardButton("♥️ دل", callback_data=f"hokm_suit_{chat_id}_♥️"),
        InlineKeyboardButton("♦️ خشت", callback_data=f"hokm_suit_{chat_id}_♦️"),
        InlineKeyboardButton("♣️ گشنیز", callback_data=f"hokm_suit_{chat_id}_♣️"),
    ]]
    return InlineKeyboardMarkup(keyboard)

def hokm_card_keyboard(hand, chat_id, player_id):
    keyboard = []
    row = []
    for i, card in enumerate(hand):
        row.append(InlineKeyboardButton(card, callback_data=f"hokm_play_{chat_id}_{player_id}_{card}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


async def start_hokm(update, context, chat_id, starter_id):
    """
    شروع بازی حکم
    starter_id = ID کاربری که بازی رو شروع کرده (فقط اون یا ادمین می‌تونن لغو کنن)
    """
    games = load_json(HOKM_FILE)
    gid = str(chat_id)

    games[gid] = {
        "state": "waiting",
        "players": [],
        "hands": {},
        "scores": {},
        "hokm_suit": None,
        "hokm_caller": None,
        "table": {},
        "turn_order": [],
        "current_turn": 0,
        "round_starter": 0,
        "tricks_won": {},
        "message_id": None,
        "starter_id": starter_id,  # 🆕 ذخیره ID شروع‌کننده
    }
    save_json(HOKM_FILE, games)

    msg = await update.message.reply_text(
        "🃏 *بازی حکم شروع شد!*\n\n"
        "برای پیوستن دکمه زیر رو بزن.\n"
        "نیاز به ۴ بازیکن داریم.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=hokm_join_keyboard(chat_id)
    )
    games[gid]["message_id"] = msg.message_id
    save_json(HOKM_FILE, games)


async def hokm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    games = load_json(HOKM_FILE)

    # ---- پیوستن ----
    if data.startswith("hokm_join_"):
        chat_id = data.split("_")[2]
        gid = str(chat_id)

        if gid not in games:
            await query.answer("بازی‌ای پیدا نشد!", show_alert=True)
            return

        game = games[gid]

        if game["state"] != "waiting":
            await query.answer("بازی شروع شده!", show_alert=True)
            return

        player_ids = [p["id"] for p in game["players"]]
        if user.id in player_ids:
            await query.answer("قبلاً پیوستی!", show_alert=True)
            return

        if len(game["players"]) >= 4:
            await query.answer("بازی پر شده!", show_alert=True)
            return

        game["players"].append({"id": user.id, "name": user.first_name})
        game["scores"][str(user.id)] = 0
        game["tricks_won"][str(user.id)] = 0

        player_list = "\n".join([f"👤 {p['name']}" for p in game["players"]])
        remaining = 4 - len(game["players"])

        await query.answer(f"✅ {user.first_name} پیوست!")

        if remaining > 0:
            await query.edit_message_text(
                f"🃏 *بازی حکم*\n\nبازیکنان:\n{player_list}\n\n"
                f"⏳ هنوز {remaining} نفر دیگه لازم داریم.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=hokm_join_keyboard(chat_id)
            )
        else:
            deck = make_deck()
            game["state"] = "choosing_suit"
            game["turn_order"] = [str(p["id"]) for p in game["players"]]

            for i, player in enumerate(game["players"]):
                pid = str(player["id"])
                game["hands"][pid] = deck[i*13:(i+1)*13]

            first_player = game["players"][0]
            game["hokm_caller"] = str(first_player["id"])
            game["round_starter"] = 0
            game["current_turn"] = 0

            player_list = "\n".join([f"👤 {p['name']}" for p in game["players"]])
            await query.edit_message_text(
                f"🃏 *بازی حکم*\n\nبازیکنان:\n{player_list}\n\n"
                f"✅ ۴ بازیکن آماده‌اند!\n"
                f"🎯 {first_player['name']} باید حکم رو انتخاب کنه.",
                parse_mode=ParseMode.MARKDOWN
            )

            for player in game["players"]:
                pid = str(player["id"])
                hand_text = " ".join(game["hands"][pid])
                try:
                    if pid == game["hokm_caller"]:
                        await context.bot.send_message(
                            player["id"],
                            f"🃏 کارت‌های تو:\n{hand_text}\n\n🎯 تو باید حکم رو انتخاب کنی:",
                            reply_markup=hokm_suit_keyboard(chat_id)
                        )
                    else:
                        await context.bot.send_message(
                            player["id"],
                            f"🃏 کارت‌های تو:\n{hand_text}\n\n⏳ منتظر انتخاب حکم باش..."
                        )
                except Exception:
                    pass

        save_json(HOKM_FILE, games)
        return

    # ---- انتخاب حکم ----
    if data.startswith("hokm_suit_"):
        parts = data.split("_")
        chat_id = parts[2]
        suit = parts[3]
        gid = str(chat_id)

        if gid not in games:
            await query.answer("بازی‌ای پیدا نشد!", show_alert=True)
            return

        game = games[gid]

        if str(user.id) != game["hokm_caller"]:
            await query.answer("نوبت تو نیست!", show_alert=True)
            return

        game["hokm_suit"] = suit
        game["state"] = "playing"
        game["current_turn"] = 0

        await query.edit_message_text(
            f"✅ حکم انتخاب شد: {suit} {SUITS[suit]}\n\n"
            f"🎮 بازی شروع می‌شه!\n"
            f"هر بازیکن باید در گروه کارتش رو انتخاب کنه."
        )

        first_pid = game["turn_order"][0]
        first_name = next(p["name"] for p in game["players"] if str(p["id"]) == first_pid)

        await context.bot.send_message(
            int(chat_id),
            f"🃏 *بازی حکم شروع شد!*\n\n"
            f"🎯 حکم: {suit} {SUITS[suit]}\n\n"
            f"نوبت: 👤 *{first_name}*\n\n"
            f"برای دیدن کارت‌هات و بازی کردن، به پیوی ربات برو.",
            parse_mode=ParseMode.MARKDOWN
        )

        first_player = next(p for p in game["players"] if str(p["id"]) == first_pid)
        hand = game["hands"][first_pid]
        try:
            await context.bot.send_message(
                first_player["id"],
                f"🎯 نوبت توئه! یه کارت بزن:\n🃏 کارت‌هات: {' '.join(hand)}",
                reply_markup=hokm_card_keyboard(hand, chat_id, first_pid)
            )
        except Exception:
            pass

        save_json(HOKM_FILE, games)
        return

    # ---- بازی کردن کارت ----
    if data.startswith("hokm_play_"):
        parts = data.split("_")
        chat_id = parts[2]
        player_id = parts[3]
        card = "_".join(parts[4:])
        gid = str(chat_id)

        if gid not in games:
            await query.answer("بازی‌ای پیدا نشد!", show_alert=True)
            return

        game = games[gid]

        if game["state"] != "playing":
            await query.answer("بازی در حال انجام نیست!", show_alert=True)
            return

        current_pid = game["turn_order"][game["current_turn"]]
        if str(user.id) != current_pid:
            await query.answer("نوبت تو نیست!", show_alert=True)
            return

        hand = game["hands"][current_pid]
        if card not in hand:
            await query.answer("این کارت رو نداری!", show_alert=True)
            return

        table = game["table"]
        if table:
            first_card = list(table.values())[0]
            lead_suit = get_card_suit(first_card)
            card_suit = get_card_suit(card)
            has_lead = any(get_card_suit(c) == lead_suit for c in hand)
            if has_lead and card_suit != lead_suit:
                await query.answer("باید همرنگ بزنی! 🚫", show_alert=True)
                return

        hand.remove(card)
        game["hands"][current_pid] = hand
        game["table"][current_pid] = card

        player_name = next(p["name"] for p in game["players"] if str(p["id"]) == current_pid)
        await query.edit_message_text(f"✅ {player_name} کارت {card} رو زد.")

        if len(game["table"]) == 4:
            winner_pid = determine_trick_winner(game)
            winner_name = next(p["name"] for p in game["players"] if str(p["id"]) == winner_pid)
            game["tricks_won"][winner_pid] = game["tricks_won"].get(winner_pid, 0) + 1

            table_display = " | ".join([f"{game['table'][pid]}" for pid in game["turn_order"]])

            await context.bot.send_message(
                int(chat_id),
                f"🃏 *دست تموم شد!*\n\n"
                f"کارت‌ها: {table_display}\n\n"
                f"🏆 برنده این دست: *{winner_name}*",
                parse_mode=ParseMode.MARKDOWN
            )

            game["table"] = {}
            winner_idx = game["turn_order"].index(winner_pid)
            game["round_starter"] = winner_idx
            game["current_turn"] = winner_idx

            if not game["hands"][game["turn_order"][0]]:
                game["state"] = "done"
                result_text = "🏆 *نتیجه بازی حکم:*\n\n"
                sorted_players = sorted(
                    game["players"],
                    key=lambda p: game["tricks_won"].get(str(p["id"]), 0),
                    reverse=True
                )
                for i, p in enumerate(sorted_players, 1):
                    tricks = game["tricks_won"].get(str(p["id"]), 0)
                    result_text += f"{i}. {p['name']} — {tricks} دست\n"

                await context.bot.send_message(
                    int(chat_id),
                    result_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                del games[gid]
                save_json(HOKM_FILE, games)
                return

        else:
            next_idx = (game["current_turn"] + 1) % 4
            game["current_turn"] = next_idx
            next_pid = game["turn_order"][next_idx]
            next_name = next(p["name"] for p in game["players"] if str(p["id"]) == next_pid)

            table_so_far = " | ".join([
                f"{game['table'][pid]}" for pid in game["turn_order"] if pid in game["table"]
            ])

            await context.bot.send_message(
                int(chat_id),
                f"🃏 روی میز: {table_so_far}\n\nنوبت: 👤 *{next_name}*",
                parse_mode=ParseMode.MARKDOWN
            )

            next_hand = game["hands"][next_pid]
            next_player = next(p for p in game["players"] if str(p["id"]) == next_pid)
            try:
                await context.bot.send_message(
                    next_player["id"],
                    f"🎯 نوبت توئه!\n🃏 کارت‌هات: {' '.join(next_hand)}\n🎯 حکم: {game['hokm_suit']}",
                    reply_markup=hokm_card_keyboard(next_hand, chat_id, next_pid)
                )
            except Exception:
                pass

        save_json(HOKM_FILE, games)
        return


def determine_trick_winner(game):
    """تعیین برنده یک دست"""
    table = game["table"]
    hokm_suit = game["hokm_suit"]
    turn_order = game["turn_order"]

    lead_pid = turn_order[game["round_starter"]]
    lead_card = table[lead_pid]
    lead_suit = get_card_suit(lead_card)

    best_pid = lead_pid
    best_card = lead_card
    best_is_hokm = (lead_suit == hokm_suit)

    for pid, card in table.items():
        if pid == lead_pid:
            continue
        suit = get_card_suit(card)
        rank = get_card_rank(card)
        best_suit = get_card_suit(best_card)
        best_rank = get_card_rank(best_card)

        card_is_hokm = (suit == hokm_suit)

        if card_is_hokm and not best_is_hokm:
            best_pid = pid
            best_card = card
            best_is_hokm = True
        elif card_is_hokm and best_is_hokm:
            if RANK_VALUES[rank] > RANK_VALUES[best_rank]:
                best_pid = pid
                best_card = card
        elif not card_is_hokm and not best_is_hokm:
            if suit == lead_suit and (best_suit != lead_suit or RANK_VALUES[rank] > RANK_VALUES[best_rank]):
                best_pid = pid
                best_card = card

    return best_pid


# ==============================
# راهنمای ربات
# ==============================

def guide_main_keyboard():
    """کیبورد منوی اصلی راهنما (با دکمه بستن)"""
    keyboard = [
        [
            InlineKeyboardButton("🃏 راهنمای حکم", callback_data="guide_hokm"),
            InlineKeyboardButton("✊ راهنمای سنگ‌کاغذقیچی", callback_data="guide_rps"),
        ],
        [
            InlineKeyboardButton("🔒 راهنمای قفل گروه", callback_data="guide_lock"),
            InlineKeyboardButton("🔇 راهنمای سکوت", callback_data="guide_mute"),
        ],
        [
            InlineKeyboardButton("💰 راهنمای قیمت‌ها", callback_data="guide_price"),
        ],
        [
            InlineKeyboardButton("❌ بستن", callback_data="guide_close"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def guide_back_keyboard():
    """کیبورد صفحه‌های داخلی راهنما (بازگشت + بستن)"""
    keyboard = [
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="guide_back"),
            InlineKeyboardButton("❌ بستن", callback_data="guide_close"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user

    # ===============================================================
    # 🔒 بررسی مالکیت پنل راهنما
    # پیام راهنما همیشه reply به پیام کاربره، پس از reply_to_message می‌خونیم
    # اگه reply_to_message وجود نداشت (مثلاً ربات مستقیم فرستاده) اجازه می‌دیم
    # ===============================================================
    reply_msg = query.message.reply_to_message
    if reply_msg is not None:
        original_sender_id = reply_msg.from_user.id
        if user.id != original_sender_id:
            await query.answer("❌ این پنل مال تو نیست!", show_alert=True)
            return

    await query.answer()

    # ❌ بستن پنل راهنما - پیام کاملاً حذف می‌شه
    if data == "guide_close":
        await query.message.delete()
        return

    # 🔙 بازگشت به منوی اصلی راهنما
    if data == "guide_back":
        await query.edit_message_text(
            "📖 *راهنمای ربات*\n\nیکی از بخش‌های زیر رو انتخاب کن:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=guide_main_keyboard()
        )
        return

    # 🃏 راهنمای حکم
    if data == "guide_hokm":
        text = (
            "🃏 *راهنمای بازی حکم*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n"
            "▫️ `حکم` — شروع بازی جدید\n"
            "▫️ `لغو حکم` — لغو بازی (فقط شروع‌کننده یا ادمین)\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🎯 *مراحل بازی:*\n\n"
            "1️⃣ یه نفر `حکم` می‌نویسه\n"
            "2️⃣ ۴ نفر روی دکمه پیوستن کلیک می‌کنن\n"
            "3️⃣ کارت‌ها در *پیوی ربات* به هر بازیکن ارسال می‌شه\n"
            "4️⃣ نفر اول از پیوی خانواده حکم رو انتخاب می‌کنه\n"
            "   (♠️ پیک / ♥️ دل / ♦️ خشت / ♣️ گشنیز)\n"
            "5️⃣ بازیکنا از پیوی کارت می‌زنن\n"
            "6️⃣ نتیجه هر دست در گروه نمایش داده می‌شه\n"
            "7️⃣ کسی که بیشترین دست رو ببره برنده‌ست\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 *قوانین:*\n\n"
            "▪️ هر بازیکن ۱۳ کارت دارد\n"
            "▪️ اگه همرنگ اول داری، *باید* همرنگ بزنی\n"
            "▪️ کارت حکم هر کارت دیگه‌ای رو می‌بره\n"
            "▪️ بین دو کارت حکم، بزرگتر می‌بره\n"
            "▪️ بزرگی کارت‌ها: 2 < 3 < ... < 10 < J < Q < K < A\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚠️ *نکته مهم:*\n"
            "همه بازیکنا باید قبلاً به ربات `/start` زده باشن\n"
            "تا ربات بتونه در پیوی بهشون پیام بده."
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    # ✊ راهنمای سنگ کاغذ قیچی
    if data == "guide_rps":
        text = (
            "✊ *راهنمای بازی سنگ، کاغذ، قیچی*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n"
            "▫️ `بازی` — شروع بازی\n"
            "▫️ `جدول بازی` — نمایش جدول برترین بازیکنان\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🎯 *نحوه بازی:*\n\n"
            "1️⃣ `بازی` بنویس\n"
            "2️⃣ یکی از سنگ، کاغذ یا قیچی رو انتخاب کن\n"
            "3️⃣ ربات هم انتخاب می‌کنه و نتیجه مشخص می‌شه\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🏆 *امتیازدهی:*\n\n"
            "▪️ برد = ۳ امتیاز ✅\n"
            "▪️ مساوی = ۱ امتیاز 🤝\n"
            "▪️ باخت = ۰ امتیاز ❌\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 *قوانین:*\n\n"
            "▪️ سنگ > قیچی\n"
            "▪️ کاغذ > سنگ\n"
            "▪️ قیچی > کاغذ"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    # 🔒 راهنمای قفل گروه
    if data == "guide_lock":
        text = (
            "🔒 *راهنمای قفل گروه*\n\n"
            "⚠️ این دستورات فقط برای *ادمین‌ها* کار می‌کنه\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔗 *قفل لینک:*\n"
            "▫️ `قفل لینک` — جلوگیری از ارسال لینک\n"
            "▫️ `باز لینک` — اجازه ارسال لینک\n\n"
            "🖼 *قفل عکس:*\n"
            "▫️ `قفل عکس` — جلوگیری از ارسال عکس\n"
            "▫️ `باز عکس` — اجازه ارسال عکس\n\n"
            "🎙 *قفل ویس:*\n"
            "▫️ `قفل ویس` — جلوگیری از ارسال ویس\n"
            "▫️ `باز ویس` — اجازه ارسال ویس\n\n"
            "↩️ *قفل فوروارد:*\n"
            "▫️ `قفل فوروارد` — جلوگیری از فوروارد پیام\n"
            "▫️ `باز فوروارد` — اجازه فوروارد پیام\n\n"
            "👑 *حالت فقط ادمین:*\n"
            "▫️ `فقط ادمین` — فقط ادمین‌ها می‌تونن پیام بزنن\n"
            "▫️ `باز همه` — همه می‌تونن پیام بزنن"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    # 🔇 راهنمای سکوت
    if data == "guide_mute":
        text = (
            "🔇 *راهنمای سکوت*\n\n"
            "⚠️ این دستورات فقط برای *ادمین‌ها* کار می‌کنه\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n\n"
            "▫️ روی پیام کاربر ریپلای بزن و بنویس:\n\n"
            "`سکوت` — سکوت دائمی\n"
            "`سکوت 10` — سکوت ۱۰ دقیقه‌ای\n"
            "`سکوت 60` — سکوت ۶۰ دقیقه‌ای\n\n"
            "▫️ برای برداشتن سکوت:\n"
            "`حذف سکوت` — (روی پیام کاربر ریپلای بزن)\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 *توضیح:*\n\n"
            "▪️ عدد بعد از سکوت = تعداد دقیقه\n"
            "▪️ اگه عدد ندی = سکوت تا زمانی که ادمین برداره"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    # 💰 راهنمای قیمت‌ها
    if data == "guide_price":
        text = (
            "💰 *راهنمای قیمت‌ها*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n\n"
            "▫️ `قیمت ارز` — نرخ دلار به تومان 💵\n"
            "▫️ `قیمت طلا` — قیمت طلای ۱۸ عیار 🥇\n"
            "▫️ `قیمت سکه` — قیمت سکه امامی 🪙\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 *توضیح:*\n\n"
            "▪️ قیمت‌ها از سایت tgju.org دریافت می‌شن\n"
            "▪️ ساعت دریافت قیمت هم نمایش داده می‌شه\n"
            "▪️ قیمت‌ها به تومان هستن"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return


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

    # راهنمای بازی
    if text == "راهنمای بازی":
        await msg.reply_text(
            "📖 *راهنمای ربات*\n\nیکی از بخش‌های زیر رو انتخاب کن:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=guide_main_keyboard()
        )
        return

    # شروع بازی سنگ کاغذ قیچی
    if text == "بازی":
        await msg.reply_text(
            "🎮 سنگ، کاغذ یا قیچی رو انتخاب کن:",
            reply_markup=rps_menu()
        )
        return

    # شروع بازی حکم
    if text == "حکم":
        games = load_json(HOKM_FILE)
        gid = str(chat.id)
        if gid in games and games[gid]["state"] in ["waiting", "playing", "choosing_suit"]:
            await msg.reply_text("⚠️ یه بازی حکم الان در جریانه! صبر کن تموم بشه.")
            return
        # 🆕 پاس دادن ID کاربر شروع‌کننده بازی
        await start_hokm(update, context, chat.id, user.id)
        return

    # 🆕 لغو بازی حکم - فقط کسی که بازی رو شروع کرده یا ادمین می‌تونه لغو کنه
    if text == "لغو حکم":
        games = load_json(HOKM_FILE)
        gid = str(chat.id)

        if gid not in games:
            await msg.reply_text("بازی حکمی در جریان نیست.")
            return

        game = games[gid]
        is_admin = member.status in ["administrator", "creator"]
        is_starter = game.get("starter_id") == user.id

        if not is_admin and not is_starter:
            # پیدا کردن اسم شروع‌کننده برای نمایش در پیام خطا
            starter_name = next(
                (p["name"] for p in game["players"] if p["id"] == game.get("starter_id")),
                "شروع‌کننده بازی"
            )
            await msg.reply_text(
                f"❌ فقط *{starter_name}* (کسی که بازی رو شروع کرده) یا ادمین می‌تونه بازی رو لغو کنه.",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        del games[gid]
        save_json(HOKM_FILE, games)
        await msg.reply_text("❌ بازی حکم لغو شد.")
        return

    # جدول بازی سنگ کاغذ قیچی
    if text == "جدول بازی":
        stats = load_json(RPS_FILE)

        if not stats:
            await msg.reply_text("هنوز کسی بازی نکرده 🎮")
            return

        sorted_players = sorted(
            stats.values(),
            key=lambda x: x["score"],
            reverse=True
        )

        message = "🏆 جدول قهرمانان:\n\n"

        for i, player in enumerate(sorted_players[:10], start=1):
            message += (
                f"{i}. {player['name']} — "
                f"{player['score']} امتیاز "
                f"(✅{player['win']} ❌{player['lose']} 🤝{player['draw']})\n"
            )

        await msg.reply_text(message)
        return

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

    if text == "ربات":
        await msg.reply_text(f"جانم {user.first_name} 😊")


# ==============================
# اجرا
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("users", users_command))
app.add_handler(CallbackQueryHandler(rps_handler, pattern="^rps_"))
app.add_handler(CallbackQueryHandler(hokm_callback, pattern="^hokm_"))
app.add_handler(CallbackQueryHandler(guide_callback, pattern="^guide_"))
app.add_handler(MessageHandler(filters.ALL, group_messages))

if __name__ == "__main__":
    app.run_polling()
