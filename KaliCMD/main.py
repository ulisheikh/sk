# main.py  (Aiogram 3) — Updated: Removed Update Functionality
import asyncio
import importlib.util
import json
import logging
import pathlib
import random
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from difflib import SequenceMatcher
from aiogram.filters import Command
from aiogram.types import Message

# ------------- CONFIG -------------
BOT_TOKEN = "8515364508:AAG6DLaVbwLirYtqpKaqupzkMLmApoMzYYw"
TC_PY = "tc.py"
STATE_FILE = "quiz_state.json"
BLOCK_INTERVAL_MIN = 12
QUESTIONS_PER_BLOCK = 5
RELOAD_CHECK_SECONDS = 3
USERS_DB = "users.db"
# ----------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DATA_DIR = pathlib.Path(".")
STATE_PATH = DATA_DIR / STATE_FILE
TC_PATH = DATA_DIR / TC_PY

# ---------- persistent state ----------
def load_state() -> Dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_state(s: Dict):
    STATE_PATH.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")

state = load_state()

# ---------- SQLite users DB ----------
def init_db():
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT,
        full_name TEXT,
        joined_at TEXT,
        last_active TEXT,
        is_subscribed INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def add_or_update_user(user: types.User, is_subscribed: Optional[bool]=None):
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    uid = user.id
    username = user.username or ""
    full_name = (user.full_name or "").strip()
    now = datetime.now().isoformat()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO users (user_id, username, full_name, joined_at, last_active, is_subscribed) VALUES (?, ?, ?, ?, ?, ?)",
            (uid, username, full_name, now, now, 1 if is_subscribed else 0)
        )
    else:
        if is_subscribed is None:
            cur.execute("UPDATE users SET username = ?, full_name = ?, last_active = ? WHERE user_id = ?", (username, full_name, now, uid))
        else:
            cur.execute("UPDATE users SET username = ?, full_name = ?, last_active = ?, is_subscribed = ? WHERE user_id = ?", (username, full_name, now, 1 if is_subscribed else 0, uid))
    conn.commit()
    conn.close()

def set_subscription_db(user_id: int, is_sub: bool):
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_subscribed = ?, last_active = ? WHERE user_id = ?", (1 if is_sub else 0, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

# ---------- load tc.py dynamically ----------
def load_ltc_from_py() -> Dict[str, Dict[str, str]]:
    if not TC_PATH.exists():
        return {}
    mtime = TC_PATH.stat().st_mtime
    if getattr(load_ltc_from_py, "cached_mtime", None) == mtime:
        return load_ltc_from_py.cached
    spec = importlib.util.spec_from_file_location("tc_module", str(TC_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for var in ("ltc", "LTC", "tc"):
        if hasattr(module, var):
            ltc = getattr(module, var)
            if isinstance(ltc, dict):
                load_ltc_from_py.cached = ltc
                load_ltc_from_py.cached_mtime = mtime
                return ltc
    load_ltc_from_py.cached = {}
    load_ltc_from_py.cached_mtime = mtime
    return {}

load_ltc_from_py.cached = {}
load_ltc_from_py.cached_mtime = None

def flatten_ltc(ltc: Dict[str, Dict[str, str]]):
    flat = []
    for ch, cmds in ltc.items():
        for k, v in cmds.items():
            flat.append((ch, k, v))
    return flat

# ---------- normalization ----------
PLACEHOLDERS = re.compile(r"\b(packagename|file|filename|<.*?>)\b", flags=re.IGNORECASE)
BRACKETS = re.compile(r"[\[\]]")

def normalize_for_compare(s: str) -> str:
    s = s or ""
    s = BRACKETS.sub("", s)
    s = PLACEHOLDERS.sub("", s)
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip("`\"' ")
    return s

def ensure_chat_state_initialized(chat_id: str, flat_questions):
    st = state.setdefault(chat_id, {})
    st.setdefault("asked", [])
    st.setdefault("current", None)
    st.setdefault("current_mode", None)
    st.setdefault("in_block", False)
    st.setdefault("remaining", 0)
    st.setdefault("next_time", None)
    st.setdefault("score", 0)
    st.setdefault("auto", False)
    st.setdefault("menu_stack", [])
    st.setdefault("continuous", False)
    if "unasked" not in st or not isinstance(st["unasked"], list):
        keys = []
        for ch, k, v in flat_questions:
            nk = normalize_for_compare(k)
            if nk:
                keys.append(nk)
        keys = list(dict.fromkeys(keys))
        random.shuffle(keys)
        st["unasked"] = keys
    return st

def pick_random_question(chat_id: str) -> Tuple[str, str, str]:
    global state
    ltc_local = load_ltc_from_py()
    FLAT = flatten_ltc(ltc_local)
    if not FLAT:
        raise RuntimeError("Savollar topilmadi.")
    st = ensure_chat_state_initialized(chat_id, FLAT)
    if not st.get("unasked"):
        keys = []
        for ch, k, v in FLAT:
            nk = normalize_for_compare(k)
            if nk:
                keys.append(nk)
        keys = list(dict.fromkeys(keys))
        random.shuffle(keys)
        st["unasked"] = keys
    chosen_norm = random.choice(st["unasked"])
    chosen_item = None
    for ch, k, v in FLAT:
        if normalize_for_compare(k) == chosen_norm:
            chosen_item = (ch, k, v)
            break
    if not chosen_item:
        st["unasked"] = []
        save_state(state)
        return pick_random_question(chat_id)
    try:
        st["unasked"].remove(chosen_norm)
    except ValueError:
        pass
    st.setdefault("asked", []).append(chosen_norm)
    save_state(state)
    return chosen_item

def compute_next_time(after_dt: Optional[datetime] = None) -> datetime:
    now = after_dt or datetime.now()
    return now + timedelta(minutes=BLOCK_INTERVAL_MIN)

stop_quiz_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛑 STOP", callback_data="menu_stop")]
])

async def send_single_question(chat_id: str):
    try:
        chapter, key, desc = pick_random_question(str(chat_id))
    except RuntimeError:
        await bot.send_message(chat_id, "Savollar mavjud emas.", reply_markup=main_menu_markup())
        return
    st = state.setdefault(str(chat_id), {})
    st["current"] = key
    st["current_mode"] = "single"
    save_state(state)
    if st.get("continuous"):
        await bot.send_message(chat_id, f"📘 <b>{chapter}</b>\n\nSavol:\n{desc}\n\nJavob yozing.", parse_mode="HTML", reply_markup=stop_quiz_kb)
    else:
        await bot.send_message(chat_id, f"📘 <b>{chapter}</b>\n\nSavol:\n{desc}\n\nJavob yozing.", parse_mode="HTML")

async def start_block_for_user(chat_id: str, questions_count: int = QUESTIONS_PER_BLOCK):
    st = state.setdefault(str(chat_id), {})
    st["in_block"] = True
    st["remaining"] = questions_count
    st["current_mode"] = "block"
    st["next_time"] = None
    save_state(state)
    await send_next_in_block(chat_id)

async def send_next_in_block(chat_id: str):
    st = state.setdefault(str(chat_id), {})
    if not st.get("in_block"):
        return
    if st.get("remaining", 0) <= 0:
        await finish_block(chat_id)
        return
    try:
        chapter, key, desc = pick_random_question(str(chat_id))
    except RuntimeError:
        await bot.send_message(chat_id, "Savollar topilmadi.", reply_markup=main_menu_markup())
        st["in_block"] = False
        st["remaining"] = 0
        save_state(state)
        return
    st["current"] = key
    st["current_mode"] = "block"
    save_state(state)
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔚 Stop", callback_data="menu_stop")]
    ])
    await bot.send_message(chat_id, f"📘 <b>{chapter}</b>\n\nSavol:\n{desc}\n\nJavob yozing.", parse_mode="HTML", reply_markup=inline_kb)

async def finish_block(chat_id: str):
    st = state.setdefault(str(chat_id), {})
    st["in_block"] = False
    st["remaining"] = 0
    st["current"] = None
    st["current_mode"] = None
    next_dt = compute_next_time(datetime.now())
    st["next_time"] = next_dt.isoformat()
    save_state(state)
    await bot.send_message(chat_id, f"✅ Blok yakunlandi. Keyingi blok { (next_dt - datetime.now()).seconds // 60 } daqiqadan so‘ng ko‘rinadi.", reply_markup=main_menu_markup())

def evaluate_answer(user_text: str, correct_key: str):
    u = normalize_for_compare(user_text)
    c = normalize_for_compare(correct_key)
    if u == c and u:
        return True, "✅ To‘g‘ri!"
    if u and (u in c or c in u):
        return False, f"🤔 Yaqin! To‘g‘ri: <code>{correct_key}</code>"
    ratio = SequenceMatcher(None, u, c).ratio()
    if ratio > 0.75:
        return False, f"⚠️ O‘xshash — lekin to‘liq emas. To‘g‘ri: <code>{correct_key}</code>"
    return False, f"❌ Noto‘g‘ri. Toʻgʻri buyruq: <code>{correct_key}</code>"

# ===== TUGMALAR (KEYBOARDS) =====

# Update tugmasi olib tashlandi
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/start")],
        [KeyboardButton(text="Menu")]
    ],
    resize_keyboard=True
)

def main_menu_markup():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="AVTOMATIK", callback_data="subscribe"),
         InlineKeyboardButton(text="GAME", callback_data="unsubscribe")],
        [InlineKeyboardButton(text="CHAPTERLAR", callback_data="menu_chapters")]
    ])

# ---------- HANDLERS ----------

@dp.message(F.text == "/start")
async def cmd_start(msg: types.Message):
    add_or_update_user(msg.from_user)
    help_text = (
        "<b>👋 Assalomu alaykum!</b>\n\n"
        "Linux buyruqlari quiz-botiga xush kelibsiz!\n"
        "----------------------------------------\n"
        "🚀 <b>Botdan foydalanish:</b>\n\n"
        "🔹 <b>AVTOMATIK</b>\t — Har 12 daqiqada 5 ta savol\n"
        "🔹 <b>GAME</b>\t\t\t\t — Cheksiz savollar (Stopgacha)\n"
        "🔹 <b>CHAPTERLAR</b>\t — Bo'limlar bo'yicha ko'rish\n"
        "----------------------------------------\n"
        "💡 <i>Yordam: Buyruq haqida bilish uchun .buyruq (masalan: .ls) deb yozing.</i>"
    )
    await msg.answer(help_text, reply_markup=main_kb, parse_mode="HTML")
    await msg.answer("<b>Asosiy menyu:</b>", reply_markup=main_menu_markup(), parse_mode="HTML")

@dp.message(F.text == "Menu")
async def msg_menu(msg: types.Message):
    add_or_update_user(msg.from_user)
    await msg.answer("<b>Asosiy menyu:</b>", reply_markup=main_menu_markup(), parse_mode="HTML")

@dp.message(F.text.startswith("."))
async def dot_info_handler(msg: types.Message):
    add_or_update_user(msg.from_user)
    key = msg.text[1:].strip()
    if not key:
        return
        
    best = None
    ltc_local = load_ltc_from_py()
    flat_local = flatten_ltc(ltc_local)
    
    for ch, k, v in flat_local:
        if normalize_for_compare(k) == normalize_for_compare(key):
            best = (k, v)
            break
            
    if not best:
        for ch, k, v in flat_local:
            if normalize_for_compare(key) in normalize_for_compare(k):
                best = (k, v)
                break
                
    if best:
        await msg.answer(f"📖 <b>Murojaat qilingan buyruq: \n> </b>{best[0]} \n\n{best[1]}", parse_mode="HTML")
    else:
        await msg.answer(f"❌ <b>{key}</b> buyrug'i topilmadi.", parse_mode="HTML")

@dp.callback_query(F.data)
async def cb_menu(cq: types.CallbackQuery):
    data = cq.data
    uid = str(cq.message.chat.id)
    add_or_update_user(cq.from_user)

    if data == "subscribe":
        st = state.setdefault(uid, {})
        st["auto"] = True
        st["continuous"] = False
        st["next_time"] = datetime.now().isoformat()
        save_state(state)
        set_subscription_db(cq.from_user.id, True)
        await cq.message.answer("✅ Avtomatik bloklar yoqildi.", reply_markup=main_kb)

    elif data == "unsubscribe":
        st = state.setdefault(uid, {})
        st["auto"] = False
        st["continuous"] = True
        st["in_block"] = False
        st["remaining"] = 0
        st["current_mode"] = None
        st["next_time"] = None
        save_state(state)
        set_subscription_db(cq.from_user.id, False)
        await cq.message.answer("🔁 Game (cheksiz savol) rejimi yoqildi.", reply_markup=main_kb)
        await asyncio.sleep(0.5)
        await send_single_question(uid)

    elif data == "menu_chapters":
        chapters = list(load_ltc_from_py().keys())
        if not chapters:
            await cq.message.answer("Hozircha bo'limlar mavjud emas.")
            await cq.answer()
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            *[[InlineKeyboardButton(text=ch, callback_data=f"view::{ch}") ] for ch in chapters],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_menu")]
        ])
        st = state.setdefault(uid, {})
        st.setdefault("menu_stack", []).append("menu_chapters")
        save_state(state)
        await cq.message.edit_text("📂 <b>Bo‘limni tanlang:</b>", reply_markup=kb, parse_mode="HTML")

    elif data.startswith("view::"):
        ch = data.split("::", 1)[1]
        ltc_local = load_ltc_from_py()
        if ch in ltc_local:
            header = f"📘 <b>{ch.upper()}</b>\n"
            header += "━━━━━━━━━━━━━━━━━━\n\n"
            lines = []
            for k, v in ltc_local[ch].items():
                line = f"▶️ <code>{k}</code>\n"
                line += f"  ┗ <i>{v}</i>\n"
                lines.append(line)
            full_text = header + "\n".join(lines)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_chapters")]
            ])
            st = state.setdefault(uid, {})
            st.setdefault("menu_stack", []).append(f"view::{ch}")
            save_state(state)
            try:
                await cq.message.edit_text(full_text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await cq.message.answer(full_text, reply_markup=kb, parse_mode="HTML")
        else:
            await cq.message.answer("Bunday bo‘lim topilmadi.")

    elif data == "menu_stop":
        st = state.setdefault(uid, {})
        st["in_block"] = False
        st["remaining"] = 0
        st["current"] = None
        st["current_mode"] = None
        st["continuous"] = False
        st["auto"] = False
        st["next_time"] = None
        save_state(state)
        await cq.message.answer("Quiz to‘xtatildi.", reply_markup=main_kb)

    elif data == "back_to_menu":
        await cq.message.edit_text("<b>Asosiy menyu:</b>", reply_markup=main_menu_markup(), parse_mode="HTML")

    elif data == "back_to_chapters":
        st = state.setdefault(uid, {})
        if st.get("menu_stack"):
            st["menu_stack"].pop()
        chapters = list(load_ltc_from_py().keys())
        kb = InlineKeyboardMarkup(inline_keyboard=[
            *[[InlineKeyboardButton(text=ch, callback_data=f"view::{ch}") ] for ch in chapters],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_menu")]
        ])
        save_state(state)
        await cq.message.edit_text("📂 <b>Bo‘limni tanlang:</b>", reply_markup=kb, parse_mode="HTML")
    await cq.answer()

@dp.message()
async def generic_handler(msg: types.Message):
    text = (msg.text or "").strip()
    if text.startswith("."):
        return
    uid = str(msg.chat.id)
    add_or_update_user(msg.from_user)
    st = state.setdefault(uid, {})
    cur = st.get("current")
    if cur:
        is_ok, feedback = evaluate_answer(text, cur)
        await msg.answer(feedback, parse_mode="HTML")
        if is_ok:
            st["score"] = st.get("score", 0) + 1
        mode = st.get("current_mode")
        st["current"] = None
        save_state(state)
        if st.get("continuous"):
            await asyncio.sleep(0.5)
            await send_single_question(uid)
            return
        if mode == "block" and st.get("in_block"):
            st["remaining"] = max(0, st.get("remaining", 0) - 1)
            save_state(state)
            if st.get("remaining", 0) > 0:
                await asyncio.sleep(0.8)
                await send_next_in_block(uid)
            else:
                await finish_block(uid)
        return
    await msg.answer("Hozir savol yo‘q. Menu tugmasini bosing.", reply_markup=main_kb)

# ---------- scheduler & loops ----------
async def scheduler_loop():
    while True:
        try:
            now = datetime.now()
            for uid, info in list(state.items()):
                if not info.get("auto") or info.get("in_block"):
                    continue
                nxt = info.get("next_time")
                if not nxt:
                    continue
                try:
                    nxt_dt = datetime.fromisoformat(nxt)
                except Exception:
                    continue
                if now >= nxt_dt:
                    asyncio.create_task(start_block_for_user(uid))
            await asyncio.sleep(RELOAD_CHECK_SECONDS)
        except Exception:
            await asyncio.sleep(5)

async def auto_reload_loop():
    while True:
        try:
            load_ltc_from_py()
        except Exception:
            pass
        await asyncio.sleep(RELOAD_CHECK_SECONDS)

async def main():
    init_db()
    asyncio.create_task(scheduler_loop())
    asyncio.create_task(auto_reload_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())