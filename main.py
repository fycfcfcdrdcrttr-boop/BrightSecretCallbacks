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
DOZ_FILE = "doz_games.json"
WORD_CHAIN_FILE = "word_chain_games.json"
NUMBER_GUESS_FILE = "number_guess_games.json"


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
# آمار بازی سنگ کاغذ قیچی
# ==============================

def update_rps_stats(user_id, name, result):
    stats = load_json(RPS_FILE)
    if str(user_id) not in stats:
        stats[str(user_id)] = {"name": name, "win": 0, "lose": 0, "draw": 0, "score": 0}
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
    emoji = {"rock": "✊ سنگ", "paper": "✋ کاغذ", "scissors": "✌ قیچی"}
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
    for card in hand:
        row.append(InlineKeyboardButton(card, callback_data=f"hokm_play_{chat_id}_{player_id}_{card}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def hokm_mode_keyboard():
    keyboard = [[
        InlineKeyboardButton("👥 دونفره", callback_data="hokm_mode_2"),
        InlineKeyboardButton("👥👥 چهارنفره", callback_data="hokm_mode_4"),
    ]]
    return InlineKeyboardMarkup(keyboard)


async def start_hokm(update, context, chat_id, starter_id):
    msg = await update.message.reply_text(
        "🃏 *بازی حکم*\n\nچند نفره بازی کنیم؟",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=hokm_mode_keyboard()
    )
    games = load_json(HOKM_FILE)
    gid = str(chat_id)
    games[gid] = {
        "state": "selecting_mode", "players": [], "hands": {}, "scores": {},
        "hokm_suit": None, "hokm_caller": None, "table": {}, "turn_order": [],
        "current_turn": 0, "round_starter": 0, "tricks_won": {},
        "message_id": msg.message_id, "starter_id": starter_id, "mode": None,
    }
    save_json(HOKM_FILE, games)


async def hokm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    games = load_json(HOKM_FILE)

    if data.startswith("hokm_mode_"):
        mode = int(data.split("_")[2])
        chat_id = str(query.message.chat_id)
        gid = chat_id
        if gid not in games or games[gid]["state"] != "selecting_mode":
            await query.answer("بازی‌ای پیدا نشد!", show_alert=True)
            return
        if games[gid]["starter_id"] != user.id:
            await query.answer("فقط کسی که بازی را شروع کرده می‌تواند حالت انتخاب کند!", show_alert=True)
            return
        games[gid]["mode"] = mode
        games[gid]["state"] = "waiting"
        save_json(HOKM_FILE, games)
        await query.answer(f"✅ حالت {'دو' if mode == 2 else 'چهار'} نفره انتخاب شد!")
        await query.edit_message_text(
            f"🃏 *بازی حکم {'دو' if mode == 2 else 'چهار'} نفره*\n\n"
            f"برای پیوستن دکمه زیر رو بزن.\nنیاز به {mode} بازیکن داریم.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=hokm_join_keyboard(chat_id)
        )
        return

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
        max_players = game.get("mode", 4)
        if len(game["players"]) >= max_players:
            await query.answer("بازی پر شده!", show_alert=True)
            return
        game["players"].append({"id": user.id, "name": user.first_name})
        game["scores"][str(user.id)] = 0
        game["tricks_won"][str(user.id)] = 0
        player_list = "\n".join([f"👤 {p['name']}" for p in game["players"]])
        remaining = max_players - len(game["players"])
        await query.answer(f"✅ {user.first_name} پیوست!")
        if remaining > 0:
            await query.edit_message_text(
                f"🃏 *بازی حکم {'دو' if max_players == 2 else 'چهار'} نفره*\n\nبازیکنان:\n{player_list}\n\n"
                f"⏳ هنوز {remaining} نفر دیگه لازم داریم.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=hokm_join_keyboard(chat_id)
            )
        else:
            deck = make_deck()
            game["state"] = "choosing_suit"
            game["turn_order"] = [str(p["id"]) for p in game["players"]]
            if max_players == 4:
                for i, player in enumerate(game["players"]):
                    game["hands"][str(player["id"])] = deck[i*13:(i+1)*13]
            else:
                for i, player in enumerate(game["players"]):
                    game["hands"][str(player["id"])] = deck[i*26:(i+1)*26]
            first_player = game["players"][0]
            game["hokm_caller"] = str(first_player["id"])
            game["round_starter"] = 0
            game["current_turn"] = 0
            player_list = "\n".join([f"👤 {p['name']}" for p in game["players"]])
            await query.edit_message_text(
                f"🃏 *بازی حکم {'دو' if max_players == 2 else 'چهار'} نفره*\n\nبازیکنان:\n{player_list}\n\n"
                f"✅ {max_players} بازیکن آماده‌اند!\n🎯 {first_player['name']} باید حکم رو انتخاب کنه.",
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
                        await context.bot.send_message(player["id"], f"🃏 کارت‌های تو:\n{hand_text}\n\n⏳ منتظر انتخاب حکم باش...")
                except Exception:
                    pass
        save_json(HOKM_FILE, games)
        return

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
        await query.edit_message_text(f"✅ حکم انتخاب شد: {suit} {SUITS[suit]}\n\n🎮 بازی شروع می‌شه!")
        first_pid = game["turn_order"][0]
        first_name = next(p["name"] for p in game["players"] if str(p["id"]) == first_pid)
        max_players = game.get("mode", 4)
        await context.bot.send_message(
            int(chat_id),
            f"🃏 *بازی حکم {'دو' if max_players == 2 else 'چهار'} نفره شروع شد!*\n\n"
            f"🎯 حکم: {suit} {SUITS[suit]}\n\nنوبت: 👤 *{first_name}*",
            parse_mode=ParseMode.MARKDOWN
        )
        first_player = next(p for p in game["players"] if str(p["id"]) == first_pid)
        hand = game["hands"][first_pid]
        try:
            await context.bot.send_message(
                first_player["id"],
                f"🎯 نوبت توئه!\n🃏 کارت‌هات: {' '.join(hand)}",
                reply_markup=hokm_card_keyboard(hand, chat_id, first_pid)
            )
        except Exception:
            pass
        save_json(HOKM_FILE, games)
        return

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
        max_players = game.get("mode", 4)
        if len(game["table"]) == max_players:
            winner_pid = determine_trick_winner(game)
            winner_name = next(p["name"] for p in game["players"] if str(p["id"]) == winner_pid)
            game["tricks_won"][winner_pid] = game["tricks_won"].get(winner_pid, 0) + 1
            table_display = " | ".join([f"{game['table'][pid]}" for pid in game["turn_order"] if pid in game["table"]])
            await context.bot.send_message(
                int(chat_id),
                f"🃏 *دست تموم شد!*\n\nکارت‌ها: {table_display}\n\n🏆 برنده این دست: *{winner_name}*",
                parse_mode=ParseMode.MARKDOWN
            )
            game["table"] = {}
            winner_idx = game["turn_order"].index(winner_pid)
            game["round_starter"] = winner_idx
            game["current_turn"] = winner_idx
            if not game["hands"][game["turn_order"][0]]:
                game["state"] = "done"
                result_text = "🏆 *نتیجه بازی حکم:*\n\n"
                sorted_players = sorted(game["players"], key=lambda p: game["tricks_won"].get(str(p["id"]), 0), reverse=True)
                for i, p in enumerate(sorted_players, 1):
                    tricks = game["tricks_won"].get(str(p["id"]), 0)
                    result_text += f"{i}. {p['name']} — {tricks} دست\n"
                await context.bot.send_message(int(chat_id), result_text, parse_mode=ParseMode.MARKDOWN)
                del games[gid]
                save_json(HOKM_FILE, games)
                return
            next_pid = winner_pid
            next_hand = game["hands"][next_pid]
            next_player = next(p for p in game["players"] if str(p["id"]) == next_pid)
            await context.bot.send_message(int(chat_id), f"نوبت: 👤 *{winner_name}* (برنده دست قبلی)", parse_mode=ParseMode.MARKDOWN)
            try:
                await context.bot.send_message(
                    next_player["id"],
                    f"🎯 نوبت توئه!\n🃏 کارت‌هات: {' '.join(next_hand)}\n🎯 حکم: {game['hokm_suit']}",
                    reply_markup=hokm_card_keyboard(next_hand, chat_id, next_pid)
                )
            except Exception:
                pass
        else:
            next_idx = (game["current_turn"] + 1) % max_players
            game["current_turn"] = next_idx
            next_pid = game["turn_order"][next_idx]
            next_name = next(p["name"] for p in game["players"] if str(p["id"]) == next_pid)
            table_so_far = " | ".join([f"{game['table'][pid]}" for pid in game["turn_order"] if pid in game["table"]])
            await context.bot.send_message(int(chat_id), f"🃏 روی میز: {table_so_far}\n\nنوبت: 👤 *{next_name}*", parse_mode=ParseMode.MARKDOWN)
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
            best_pid = pid; best_card = card; best_is_hokm = True
        elif card_is_hokm and best_is_hokm:
            if RANK_VALUES[rank] > RANK_VALUES[best_rank]:
                best_pid = pid; best_card = card
        elif not card_is_hokm and not best_is_hokm:
            if suit == lead_suit and (best_suit != lead_suit or RANK_VALUES[rank] > RANK_VALUES[best_rank]):
                best_pid = pid; best_card = card
    return best_pid


# ==============================
# بازی دوز
# ==============================

def doz_board_keyboard(board, game_id):
    symbols = {None: "⬜", "X": "❌", "O": "⭕"}
    keyboard = []
    for row in range(3):
        kb_row = []
        for col in range(3):
            idx = row * 3 + col
            kb_row.append(InlineKeyboardButton(symbols[board[idx]], callback_data=f"doz_move_{game_id}_{idx}"))
        keyboard.append(kb_row)
    return InlineKeyboardMarkup(keyboard)

def doz_check_winner(board):
    for combo in [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]:
        if board[combo[0]] and board[combo[0]] == board[combo[1]] == board[combo[2]]:
            return board[combo[0]]
    if all(cell is not None for cell in board):
        return "draw"
    return None

def doz_board_text(board, game):
    p1_name = game["players"][0]["name"]
    p2_name = game["players"][1]["name"] if len(game["players"]) > 1 else "منتظر..."
    current_idx = game["current_turn"]
    current_name = game["players"][current_idx]["name"] if len(game["players"]) > current_idx else "؟"
    return (
        f"🎮 *بازی دوز*\n\n"
        f"❌ {p1_name}  vs  ⭕ {p2_name}\n\n"
        f"نوبت: {'❌' if current_idx == 0 else '⭕'} *{current_name}*"
    )

async def doz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    games = load_json(DOZ_FILE)

    if data.startswith("doz_join_"):
        game_id = data.split("_")[2]
        if game_id not in games:
            await query.answer("بازی پیدا نشد!", show_alert=True)
            return
        game = games[game_id]
        if game["state"] != "waiting":
            await query.answer("بازی شروع شده!", show_alert=True)
            return
        if user.id in [p["id"] for p in game["players"]]:
            await query.answer("قبلاً پیوستی!", show_alert=True)
            return
        if len(game["players"]) >= 2:
            await query.answer("بازی پر شده!", show_alert=True)
            return
        game["players"].append({"id": user.id, "name": user.first_name})
        game["state"] = "playing"
        save_json(DOZ_FILE, games)
        await query.answer(f"✅ {user.first_name} پیوست!")
        await query.edit_message_text(
            doz_board_text(game["board"], game),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=doz_board_keyboard(game["board"], game_id)
        )
        return

    if data.startswith("doz_move_"):
        parts = data.split("_")
        game_id = parts[2]
        cell_idx = int(parts[3])
        if game_id not in games:
            await query.answer("بازی پیدا نشد!", show_alert=True)
            return
        game = games[game_id]
        if game["state"] != "playing":
            await query.answer("بازی در جریان نیست!", show_alert=True)
            return
        current_player = game["players"][game["current_turn"]]
        if user.id != current_player["id"]:
            await query.answer("نوبت تو نیست!", show_alert=True)
            return
        board = game["board"]
        if board[cell_idx] is not None:
            await query.answer("این خونه پر هست!", show_alert=True)
            return
        symbol = "X" if game["current_turn"] == 0 else "O"
        board[cell_idx] = symbol
        game["board"] = board
        winner = doz_check_winner(board)
        if winner == "draw":
            await query.answer("مساوی!")
            await query.edit_message_text(
                f"🎮 *بازی دوز*\n\n🤝 *مساوی شد!*\n\n❌ {game['players'][0]['name']}  vs  ⭕ {game['players'][1]['name']}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=doz_board_keyboard(board, game_id)
            )
            del games[game_id]
            save_json(DOZ_FILE, games)
        elif winner:
            winner_name = current_player["name"]
            await query.answer(f"🎉 {winner_name} برد!")
            await query.edit_message_text(
                f"🎮 *بازی دوز*\n\n🏆 *{winner_name} برد!* {'❌' if winner == 'X' else '⭕'}\n\n"
                f"❌ {game['players'][0]['name']}  vs  ⭕ {game['players'][1]['name']}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=doz_board_keyboard(board, game_id)
            )
            del games[game_id]
            save_json(DOZ_FILE, games)
        else:
            game["current_turn"] = 1 - game["current_turn"]
            save_json(DOZ_FILE, games)
            await query.answer("✅")
            await query.edit_message_text(
                doz_board_text(board, game),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=doz_board_keyboard(board, game_id)
            )


# ==============================
# بازی کلمه‌بازی زنجیری
# ==============================

def normalize_persian(text):
    text = text.strip()
    text = text.replace("ي", "ی").replace("ك", "ک")
    return text

def get_last_char(word):
    word = normalize_persian(word)
    return word[-1] if word else ""

def get_first_char(word):
    word = normalize_persian(word)
    return word[0] if word else ""

async def word_chain_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    games = load_json(WORD_CHAIN_FILE)

    if data.startswith("wchain_join_"):
        game_id = data.split("_")[2]
        if game_id not in games:
            await query.answer("بازی پیدا نشد!", show_alert=True)
            return
        game = games[game_id]
        if game["state"] != "waiting":
            await query.answer("بازی شروع شده!", show_alert=True)
            return
        if user.id in [p["id"] for p in game["players"]]:
            await query.answer("قبلاً پیوستی!", show_alert=True)
            return
        if len(game["players"]) >= 2:
            await query.answer("بازی پر شده!", show_alert=True)
            return

        game["players"].append({"id": user.id, "name": user.first_name})
        game["state"] = "playing"
        game["current_turn"] = 0

        start_words = ["آب", "باران", "نان", "نور", "راه", "هوا", "امید", "دریا", "یاس", "سیب", "گل", "لاله", "ایران", "نهر", "رود"]
        start_word = random.choice(start_words)
        game["last_word"] = start_word
        game["used_words"] = [start_word]

        save_json(WORD_CHAIN_FILE, games)
        await query.answer(f"✅ {user.first_name} پیوست!")

        p1 = game["players"][0]["name"]
        p2 = game["players"][1]["name"]
        current_name = game["players"][0]["name"]
        last_char = get_last_char(start_word)

        await query.edit_message_text(
            f"🔤 *بازی کلمه‌بازی زنجیری شروع شد!*\n\n"
            f"👤 {p1}  vs  👤 {p2}\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📌 کلمه شروع: *{start_word}*\n"
            f"🔡 آخرین حرف: *{last_char}*\n\n"
            f"نوبت: 👤 *{current_name}*\n"
            f"یه کلمه فارسی بنویس که با «*{last_char}*» شروع بشه!",
            parse_mode=ParseMode.MARKDOWN
        )


# ==============================
# بازی گاو و گوسفند
# ==============================

def generate_secret_number():
    digits = random.sample("0123456789", 4)
    while digits[0] == "0":
        random.shuffle(digits)
    return "".join(digits)

def check_guess(secret, guess):
    cows = sum(s == g for s, g in zip(secret, guess))
    bulls = sum(g in secret for g in guess) - cows
    return cows, bulls

async def numguess_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    games = load_json(NUMBER_GUESS_FILE)

    if data.startswith("numguess_join_"):
        game_id = data.split("_")[2]
        if game_id not in games:
            await query.answer("بازی پیدا نشد!", show_alert=True)
            return
        game = games[game_id]
        if game["state"] != "waiting":
            await query.answer("بازی شروع شده!", show_alert=True)
            return
        if user.id in [p["id"] for p in game["players"]]:
            await query.answer("قبلاً پیوستی!", show_alert=True)
            return
        if len(game["players"]) >= 2:
            await query.answer("بازی پر شده!", show_alert=True)
            return

        game["players"].append({"id": user.id, "name": user.first_name})
        game["state"] = "playing"
        game["current_turn"] = 0
        game["attempts"][user.first_name] = []
        save_json(NUMBER_GUESS_FILE, games)

        await query.answer(f"✅ {user.first_name} پیوست!")
        p1 = game["players"][0]["name"]
        p2 = game["players"][1]["name"]
        current_name = game["players"][0]["name"]

        await query.edit_message_text(
            f"🔢 *بازی گاو و گوسفند شروع شد!*\n\n"
            f"👤 {p1}  vs  👤 {p2}\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🤖 ربات یه عدد ۴ رقمی (بدون تکرار) در ذهن داره!\n\n"
            f"نوبت: 👤 *{current_name}*\n"
            f"یه عدد ۴ رقمی حدس بزن (مثلاً: 1234)",
            parse_mode=ParseMode.MARKDOWN
        )


# ==============================
# راهنمای ربات
# ==============================

def guide_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🃏 حکم ۴نفره", callback_data="guide_hokm4"),
            InlineKeyboardButton("🃏 حکم ۲نفره", callback_data="guide_hokm2"),
        ],
        [
            InlineKeyboardButton("✊ سنگ‌کاغذقیچی", callback_data="guide_rps"),
            InlineKeyboardButton("⭕ دوز", callback_data="guide_doz"),
        ],
        [
            InlineKeyboardButton("🔤 کلمه‌بازی زنجیری", callback_data="guide_wordchain"),
            InlineKeyboardButton("🔢 گاو و گوسفند", callback_data="guide_numguess"),
        ],
        [
            InlineKeyboardButton("🔒 قفل گروه", callback_data="guide_lock"),
            InlineKeyboardButton("🔇 سکوت", callback_data="guide_mute"),
        ],
        [
            InlineKeyboardButton("💰 قیمت‌ها", callback_data="guide_price"),
        ],
        [
            InlineKeyboardButton("❌ بستن", callback_data="guide_close"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def guide_back_keyboard():
    keyboard = [[
        InlineKeyboardButton("🔙 بازگشت", callback_data="guide_back"),
        InlineKeyboardButton("❌ بستن", callback_data="guide_close"),
    ]]
    return InlineKeyboardMarkup(keyboard)


async def guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user

    reply_msg = query.message.reply_to_message
    if reply_msg is not None:
        if user.id != reply_msg.from_user.id:
            await query.answer("❌ این پنل مال تو نیست!", show_alert=True)
            return

    await query.answer()

    if data == "guide_close":
        await query.message.delete()
        return

    if data == "guide_back":
        await query.edit_message_text(
            "📖 *راهنمای ربات*\n\nیکی از بخش‌های زیر رو انتخاب کن:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=guide_main_keyboard()
        )
        return

    if data == "guide_hokm4":
        text = (
            "🃏 *راهنمای بازی حکم ۴ نفره*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n"
            "▫️ `حکم` — شروع بازی جدید\n"
            "▫️ `لغو حکم` — لغو بازی\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🎯 *مراحل بازی:*\n\n"
            "1️⃣ `حکم` بنویس و حالت ۴ نفره انتخاب کن\n"
            "2️⃣ ۴ نفر روی دکمه پیوستن کلیک کنن\n"
            "3️⃣ کارت‌ها در *پیوی ربات* ارسال می‌شه\n"
            "4️⃣ نفر اول حکم رو انتخاب می‌کنه\n"
            "5️⃣ بازیکنا از پیوی کارت می‌زنن\n"
            "6️⃣ نتیجه هر دست در گروه نمایش داده می‌شه\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 *قوانین:*\n\n"
            "▪️ هر بازیکن ۱۳ کارت دارد\n"
            "▪️ اگه همرنگ اول داری، *باید* همرنگ بزنی\n"
            "▪️ کارت حکم هر کارت دیگه‌ای رو می‌بره\n"
            "▪️ بزرگی: 2 < 3 < ... < 10 < J < Q < K < A\n\n"
            "⚠️ همه بازیکنا باید قبلاً `/start` زده باشن"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    if data == "guide_hokm2":
        text = (
            "🃏 *راهنمای بازی حکم ۲ نفره*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n"
            "▫️ `حکم` — شروع بازی جدید\n"
            "▫️ `لغو حکم` — لغو بازی\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🎯 *مراحل بازی:*\n\n"
            "1️⃣ `حکم` بنویس و حالت *۲ نفره* انتخاب کن\n"
            "2️⃣ نفر دوم روی دکمه پیوستن کلیک کنه\n"
            "3️⃣ هر بازیکن *۲۶ کارت* در پیوی دریافت می‌کنه\n"
            "4️⃣ نفر اول حکم رو انتخاب می‌کنه\n"
            "5️⃣ بازیکنا از پیوی کارت می‌زنن\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 *قوانین مخصوص ۲ نفره:*\n\n"
            "▪️ هر بازیکن ۲۶ کارت دارد\n"
            "▪️ در هر دست، هر نفر ۱ کارت می‌زند\n"
            "▪️ برنده هر دست، دست بعدی را شروع می‌کند\n"
            "▪️ مجموع دست‌ها ۲۶ تاست\n"
            "▪️ برنده کسی‌ست که بیشتر از ۱۳ دست ببره\n\n"
            "⚠️ هر دو باید قبلاً `/start` زده باشن"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    if data == "guide_doz":
        text = (
            "⭕ *راهنمای بازی دوز*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n"
            "▫️ `دوز` — شروع بازی جدید\n"
            "▫️ `لغو دوز` — لغو بازی جاری\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🎯 *مراحل بازی:*\n\n"
            "1️⃣ یه نفر `دوز` می‌نویسه\n"
            "2️⃣ نفر دوم روی دکمه پیوستن کلیک می‌کنه\n"
            "3️⃣ نفر اول ❌ و نفر دوم ⭕ هست\n"
            "4️⃣ هر نفر در نوبت خودش یه خونه رو انتخاب می‌کنه\n"
            "5️⃣ اولی که ۳ خونه پشت هم بچینه برنده‌ست!\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 *قوانین:*\n\n"
            "▪️ خونه‌ای که پر شده قابل انتخاب نیست\n"
            "▪️ برد: ۳ علامت پشت هم (ردیف، ستون یا قطر)\n"
            "▪️ اگه همه ۹ خونه پر بشن = مساوی!"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    if data == "guide_wordchain":
        text = (
            "🔤 *راهنمای بازی کلمه‌بازی زنجیری*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n"
            "▫️ `کلمه بازی` — شروع بازی جدید\n"
            "▫️ `لغو کلمه` — لغو بازی جاری\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🎯 *مراحل بازی:*\n\n"
            "1️⃣ یه نفر `کلمه بازی` می‌نویسه\n"
            "2️⃣ نفر دوم روی دکمه پیوستن کلیک می‌کنه\n"
            "3️⃣ ربات یه کلمه شروع تصادفی اعلام می‌کنه\n"
            "4️⃣ هر نفر به نوبت یه کلمه فارسی *در همین گروه* می‌نویسه\n"
            "5️⃣ ربات داوری می‌کنه — اگه اشتباه باشه، بازی تموم می‌شه\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 *قوانین:*\n\n"
            "▪️ کلمه باید با *آخرین حرف* کلمه قبلی شروع بشه\n"
            "▪️ کلمه‌های *تکراری* قبول نیست\n"
            "▪️ کلمه باید *فارسی* باشه (بدون عدد و انگلیسی)\n"
            "▪️ اگه کسی اشتباه بگه یا تکراری بگه، *می‌بازه!*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "💡 *مثال:*\n\n"
            "🤖 کلمه شروع: *آب*\n"
            "👤 نفر اول: *باران* ✅ (با «ب» شروع شد)\n"
            "👤 نفر دوم: *نان* ✅ (با «ن» شروع شد)\n"
            "👤 نفر اول: *نور* ✅ (با «ن» شروع شد)\n"
            "👤 نفر دوم: *نان* ❌ تکراری! ← می‌بازه"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    if data == "guide_numguess":
        text = (
            "🔢 *راهنمای بازی گاو و گوسفند*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n"
            "▫️ `عدد بازی` — شروع بازی جدید\n"
            "▫️ `لغو عدد` — لغو بازی جاری\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🎯 *مراحل بازی:*\n\n"
            "1️⃣ یه نفر `عدد بازی` می‌نویسه\n"
            "2️⃣ نفر دوم روی دکمه پیوستن کلیک می‌کنه\n"
            "3️⃣ ربات یه عدد ۴ رقمی مخفی انتخاب می‌کنه\n"
            "4️⃣ بازیکنا به نوبت یه عدد ۴ رقمی حدس می‌زنن\n"
            "5️⃣ ربات نتیجه رو اعلام می‌کنه\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🐄 *گاو* = رقم درست، جای *درست*\n"
            "🐑 *گوسفند* = رقم درست، جای *اشتباه*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "💡 *مثال:*\n\n"
            "🤖 عدد مخفی: *۱۳۵۷*\n\n"
            "حدس *۱۲۳۴* ← 🐄۱  🐑۱\n"
            "حدس *۱۳۵۹* ← 🐄۳  🐑۰\n"
            "حدس *۱۳۵۷* ← 🐄۴  🎉 *برنده!*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 *قوانین:*\n\n"
            "▪️ عدد ۴ رقمی *بدون تکرار*\n"
            "▪️ هر بازیکن حداکثر *۸ تلاش* دارد\n"
            "▪️ کسی که زودتر ۴ گاو بگیره برنده‌ست\n"
            "▪️ هر دو ۸ تلاش = مساوی"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    if data == "guide_rps":
        text = (
            "✊ *راهنمای بازی سنگ، کاغذ، قیچی*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 *دستورات:*\n"
            "▫️ `بازی` — شروع بازی\n"
            "▫️ `جدول بازی` — جدول برترین بازیکنان\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🎯 *نحوه بازی:*\n\n"
            "1️⃣ `بازی` بنویس\n"
            "2️⃣ سنگ، کاغذ یا قیچی انتخاب کن\n"
            "3️⃣ ربات هم انتخاب می‌کنه و نتیجه مشخص می‌شه\n\n"
            "🏆 برد=۳ امتیاز | مساوی=۱ امتیاز | باخت=۰\n\n"
            "📋 سنگ>قیچی | کاغذ>سنگ | قیچی>کاغذ"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    if data == "guide_lock":
        text = (
            "🔒 *راهنمای قفل گروه*\n\n"
            "⚠️ فقط برای *ادمین‌ها*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "▫️ `قفل لینک` / `باز لینک`\n"
            "▫️ `قفل عکس` / `باز عکس`\n"
            "▫️ `قفل ویس` / `باز ویس`\n"
            "▫️ `قفل فوروارد` / `باز فوروارد`\n"
            "▫️ `فقط ادمین` / `باز همه`"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    if data == "guide_mute":
        text = (
            "🔇 *راهنمای سکوت*\n\n"
            "⚠️ فقط برای *ادمین‌ها*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "روی پیام کاربر ریپلای بزن:\n\n"
            "`سکوت` — سکوت دائمی\n"
            "`سکوت 10` — سکوت ۱۰ دقیقه‌ای\n"
            "`حذف سکوت` — برداشتن سکوت"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=guide_back_keyboard())
        return

    if data == "guide_price":
        text = (
            "💰 *راهنمای قیمت‌ها*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "▫️ `قیمت ارز` — نرخ دلار 💵\n"
            "▫️ `قیمت طلا` — طلای ۱۸ عیار 🥇\n"
            "▫️ `قیمت سکه` — سکه امامی 🪙\n\n"
            "قیمت‌ها از tgju.org — به تومان"
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

    # ==============================
    # تکرار کردن پیام
    # ==============================
    if text.startswith("تکرار "):
        repeat_text = text[len("تکرار "):].strip()
        if repeat_text:
            await msg.reply_text(repeat_text)
        return

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
        await msg.reply_text("🎮 سنگ، کاغذ یا قیچی رو انتخاب کن:", reply_markup=rps_menu())
        return

    # ==============================
    # بازی کلمه‌بازی زنجیری — شروع
    # ==============================
    if text == "کلمه بازی":
        wc_games = load_json(WORD_CHAIN_FILE)
        game_id = str(chat.id)
        if game_id in wc_games and wc_games[game_id]["state"] in ["waiting", "playing"]:
            await msg.reply_text("⚠️ یه بازی کلمه‌بازی الان در جریانه!")
            return
        wc_games[game_id] = {
            "state": "waiting",
            "players": [{"id": user.id, "name": user.first_name}],
            "current_turn": 0, "last_word": "", "used_words": [],
            "starter_id": user.id,
        }
        save_json(WORD_CHAIN_FILE, wc_games)
        keyboard = [[InlineKeyboardButton("🔤 پیوستن به بازی", callback_data=f"wchain_join_{game_id}")]]
        await msg.reply_text(
            f"🔤 *کلمه‌بازی زنجیری*\n\n👤 {user.first_name} بازی رو شروع کرد!\nیه نفر دیگه باید بپیونده.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if text == "لغو کلمه":
        wc_games = load_json(WORD_CHAIN_FILE)
        game_id = str(chat.id)
        if game_id not in wc_games:
            await msg.reply_text("بازی کلمه‌بازی‌ای در جریان نیست.")
            return
        is_admin = member.status in ["administrator", "creator"]
        is_starter = wc_games[game_id].get("starter_id") == user.id
        if not is_admin and not is_starter:
            await msg.reply_text("❌ فقط شروع‌کننده یا ادمین می‌تونه لغو کنه.")
            return
        del wc_games[game_id]
        save_json(WORD_CHAIN_FILE, wc_games)
        await msg.reply_text("❌ بازی کلمه‌بازی لغو شد.")
        return

    # ==============================
    # پردازش کلمه در بازی زنجیری
    # ==============================
    wc_games = load_json(WORD_CHAIN_FILE)
    wc_game_id = str(chat.id)
    if wc_game_id in wc_games and wc_games[wc_game_id]["state"] == "playing" and text:
        game = wc_games[wc_game_id]
        current_player = game["players"][game["current_turn"]]

        if user.id == current_player["id"]:
            word = normalize_persian(text)

            # فقط پیام‌هایی که احتمالاً کلمه فارسی هستن پردازش می‌شن
            # (از دستورات دیگه جلوگیری می‌کنیم)
            skip_commands = ["راهنمای بازی", "بازی", "دوز", "حکم", "عدد بازی", "جدول بازی",
                           "قیمت ارز", "قیمت طلا", "قیمت سکه", "ربات", "لغو دوز", "لغو حکم", "لغو عدد"]
            if word in skip_commands or word.startswith("تکرار ") or word.startswith("سکوت") or word == "حذف سکوت":
                pass
            elif not re.match(r'^[\u0600-\u06FF]+$', word):
                # نه فارسی خالص — نادیده بگیر (شاید دستور دیگه‌ای بوده)
                pass
            else:
                # بررسی تکراری بودن
                if word in game["used_words"]:
                    winner_idx = 1 - game["current_turn"]
                    winner_name = game["players"][winner_idx]["name"]
                    await msg.reply_text(
                        f"❌ *{user.first_name}* کلمه «{word}» قبلاً گفته شده!\n\n"
                        f"🏆 *{winner_name}* برنده شد!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    del wc_games[wc_game_id]
                    save_json(WORD_CHAIN_FILE, wc_games)
                    return

                # بررسی حرف اول
                last_word = game["last_word"]
                required_first = get_last_char(last_word)
                actual_first = get_first_char(word)

                if required_first and actual_first != required_first:
                    winner_idx = 1 - game["current_turn"]
                    winner_name = game["players"][winner_idx]["name"]
                    await msg.reply_text(
                        f"❌ *{user.first_name}* کلمه باید با «{required_first}» شروع بشه!\n"
                        f"تو با «{actual_first}» شروع کردی.\n\n"
                        f"🏆 *{winner_name}* برنده شد!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    del wc_games[wc_game_id]
                    save_json(WORD_CHAIN_FILE, wc_games)
                    return

                # کلمه درسته!
                game["used_words"].append(word)
                game["last_word"] = word
                game["current_turn"] = 1 - game["current_turn"]
                next_player = game["players"][game["current_turn"]]
                last_char = get_last_char(word)
                save_json(WORD_CHAIN_FILE, wc_games)

                await msg.reply_text(
                    f"✅ *{word}* — قبول شد!\n\n"
                    f"🔡 آخرین حرف: *{last_char}*\n"
                    f"نوبت: 👤 *{next_player['name']}*\n"
                    f"با «*{last_char}*» شروع کن!",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

    # ==============================
    # بازی گاو و گوسفند — شروع
    # ==============================
    if text == "عدد بازی":
        ng_games = load_json(NUMBER_GUESS_FILE)
        game_id = str(chat.id)
        if game_id in ng_games and ng_games[game_id]["state"] in ["waiting", "playing"]:
            await msg.reply_text("⚠️ یه بازی گاو و گوسفند الان در جریانه!")
            return
        secret = generate_secret_number()
        ng_games[game_id] = {
            "state": "waiting",
            "players": [{"id": user.id, "name": user.first_name}],
            "secret": secret, "current_turn": 0,
            "attempts": {user.first_name: []},
            "max_attempts": 8, "starter_id": user.id,
        }
        save_json(NUMBER_GUESS_FILE, ng_games)
        keyboard = [[InlineKeyboardButton("🔢 پیوستن به بازی", callback_data=f"numguess_join_{game_id}")]]
        await msg.reply_text(
            f"🔢 *بازی گاو و گوسفند*\n\n👤 {user.first_name} بازی رو شروع کرد!\nیه نفر دیگه باید بپیونده.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if text == "لغو عدد":
        ng_games = load_json(NUMBER_GUESS_FILE)
        game_id = str(chat.id)
        if game_id not in ng_games:
            await msg.reply_text("بازی گاو و گوسفندی در جریان نیست.")
            return
        is_admin = member.status in ["administrator", "creator"]
        is_starter = ng_games[game_id].get("starter_id") == user.id
        if not is_admin and not is_starter:
            await msg.reply_text("❌ فقط شروع‌کننده یا ادمین می‌تونه لغو کنه.")
            return
        secret = ng_games[game_id]["secret"]
        del ng_games[game_id]
        save_json(NUMBER_GUESS_FILE, ng_games)
        await msg.reply_text(f"❌ بازی لغو شد.\n🔢 عدد مخفی: *{secret}* بود", parse_mode=ParseMode.MARKDOWN)
        return

    # ==============================
    # پردازش حدس در بازی گاو و گوسفند
    # ==============================
    ng_games = load_json(NUMBER_GUESS_FILE)
    ng_game_id = str(chat.id)
    if ng_game_id in ng_games and ng_games[ng_game_id]["state"] == "playing" and text:
        game = ng_games[ng_game_id]
        current_player = game["players"][game["current_turn"]]

        if user.id == current_player["id"] and re.match(r'^\d{4}$', text):
            guess = text
            secret = game["secret"]

            if len(set(guess)) != 4:
                await msg.reply_text("❌ عدد باید ۴ رقم *بدون تکرار* باشه!", parse_mode=ParseMode.MARKDOWN)
                return

            cows, bulls = check_guess(secret, guess)
            player_name = current_player["name"]

            if player_name not in game["attempts"]:
                game["attempts"][player_name] = []
            game["attempts"][player_name].append(guess)
            attempt_num = len(game["attempts"][player_name])

            if cows == 4:
                await msg.reply_text(
                    f"🎉 *{player_name}* برنده شد!\n\n"
                    f"حدس: *{guess}*\n🐄 گاو: ۴\n\n"
                    f"در *{attempt_num}* تلاش حدس زد!",
                    parse_mode=ParseMode.MARKDOWN
                )
                del ng_games[ng_game_id]
                save_json(NUMBER_GUESS_FILE, ng_games)
                return

            result_text = (
                f"🔢 *{player_name}* حدس زد: *{guess}*\n"
                f"🐄 گاو: {cows}  🐑 گوسفند: {bulls}\n"
                f"📊 تلاش {attempt_num} از {game['max_attempts']}"
            )

            other_idx = 1 - game["current_turn"]
            other_player = game["players"][other_idx]
            other_name = other_player["name"]

            if attempt_num >= game["max_attempts"]:
                other_attempts = len(game["attempts"].get(other_name, []))
                if other_attempts >= game["max_attempts"]:
                    await msg.reply_text(
                        result_text + f"\n\n🤝 *مساوی شد!*\n🔢 عدد مخفی: *{secret}* بود",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    del ng_games[ng_game_id]
                    save_json(NUMBER_GUESS_FILE, ng_games)
                    return
                else:
                    await msg.reply_text(
                        result_text + f"\n\n⚠️ *{player_name}* تلاش‌هاش تموم شد!\nنوبت: 👤 *{other_name}*",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    game["current_turn"] = other_idx
                    save_json(NUMBER_GUESS_FILE, ng_games)
                    return

            game["current_turn"] = other_idx
            save_json(NUMBER_GUESS_FILE, ng_games)

            await msg.reply_text(
                result_text + f"\n\nنوبت: 👤 *{other_player['name']}*",
                parse_mode=ParseMode.MARKDOWN
            )
            return

    # شروع بازی دوز
    if text == "دوز":
        doz_games = load_json(DOZ_FILE)
        game_id = str(chat.id)
        if game_id in doz_games and doz_games[game_id]["state"] in ["waiting", "playing"]:
            await msg.reply_text("⚠️ یه بازی دوز الان در جریانه!")
            return
        doz_games[game_id] = {
            "state": "waiting",
            "players": [{"id": user.id, "name": user.first_name}],
            "board": [None] * 9, "current_turn": 0, "starter_id": user.id,
        }
        save_json(DOZ_FILE, doz_games)
        keyboard = [[InlineKeyboardButton("🎮 پیوستن به بازی دوز", callback_data=f"doz_join_{game_id}")]]
        await msg.reply_text(
            f"⭕ *بازی دوز*\n\n👤 {user.first_name} بازی رو شروع کرد!\nیه نفر دیگه باید بپیونده.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if text == "لغو دوز":
        doz_games = load_json(DOZ_FILE)
        game_id = str(chat.id)
        if game_id not in doz_games:
            await msg.reply_text("بازی دوزی در جریان نیست.")
            return
        is_admin = member.status in ["administrator", "creator"]
        is_starter = doz_games[game_id].get("starter_id") == user.id
        if not is_admin and not is_starter:
            await msg.reply_text("❌ فقط شروع‌کننده یا ادمین می‌تونه لغو کنه.")
            return
        del doz_games[game_id]
        save_json(DOZ_FILE, doz_games)
        await msg.reply_text("❌ بازی دوز لغو شد.")
        return

    # شروع بازی حکم
    if text == "حکم":
        games = load_json(HOKM_FILE)
        gid = str(chat.id)
        if gid in games and games[gid]["state"] in ["waiting", "playing", "choosing_suit", "selecting_mode"]:
            await msg.reply_text("⚠️ یه بازی حکم الان در جریانه!")
            return
        await start_hokm(update, context, chat.id, user.id)
        return

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
            starter_name = next((p["name"] for p in game["players"] if p["id"] == game.get("starter_id")), "شروع‌کننده")
            await msg.reply_text(f"❌ فقط *{starter_name}* یا ادمین می‌تونه لغو کنه.", parse_mode=ParseMode.MARKDOWN)
            return
        del games[gid]
        save_json(HOKM_FILE, games)
        await msg.reply_text("❌ بازی حکم لغو شد.")
        return

    # جدول بازی
    if text == "جدول بازی":
        stats = load_json(RPS_FILE)
        if not stats:
            await msg.reply_text("هنوز کسی بازی نکرده 🎮")
            return
        sorted_players = sorted(stats.values(), key=lambda x: x["score"], reverse=True)
        message = "🏆 جدول قهرمانان:\n\n"
        for i, player in enumerate(sorted_players[:10], start=1):
            message += f"{i}. {player['name']} — {player['score']} امتیاز (✅{player['win']} ❌{player['lose']} 🤝{player['draw']})\n"
        await msg.reply_text(message)
        return

    # ==============================
    # مدیریت قفل‌ها
    # ==============================

    locks = load_json(LOCK_FILE)
    gid = str(chat.id)
    if gid not in locks:
        locks[gid] = {"link": False, "photo": False, "voice": False, "forward": False, "only_admin": False}

    if member.status in ["administrator", "creator"]:
        lock_commands = {
            "قفل لینک": ("link", True), "باز لینک": ("link", False),
            "قفل عکس": ("photo", True), "باز عکس": ("photo", False),
            "قفل ویس": ("voice", True), "باز ویس": ("voice", False),
            "قفل فوروارد": ("forward", True), "باز فوروارد": ("forward", False),
            "فقط ادمین": ("only_admin", True), "باز همه": ("only_admin", False),
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
            await context.bot.restrict_chat_member(chat.id, target.id, ChatPermissions(can_send_messages=False), until_date=until)
        else:
            await context.bot.restrict_chat_member(chat.id, target.id, ChatPermissions(can_send_messages=False))
        muted[str(target.id)] = target.first_name
        save_json(MUTE_FILE, muted)
        await msg.reply_text(f"🔇 {target.first_name} سکوت شد.")
        return

    if text == "حذف سکوت" and msg.reply_to_message:
        if member.status not in ["administrator", "creator"]:
            return
        target = msg.reply_to_message.from_user
        await context.bot.restrict_chat_member(chat.id, target.id, ChatPermissions(can_send_messages=True), until_date=None)
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
app.add_handler(CallbackQueryHandler(doz_callback, pattern="^doz_"))
app.add_handler(CallbackQueryHandler(word_chain_callback, pattern="^wchain_"))
app.add_handler(CallbackQueryHandler(numguess_callback, pattern="^numguess_"))
app.add_handler(CallbackQueryHandler(guide_callback, pattern="^guide_"))
app.add_handler(MessageHandler(filters.ALL, group_messages))

if __name__ == "__main__":
    app.run_polling()
