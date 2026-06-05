import os
import re
import time
import random
import requests
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PROXYAPI_KEY = os.environ.get("PROXYAPI_KEY")

BOT_USERNAME = "RbIjbIK_bot"
TZ = timezone(timedelta(hours=5))

MODEL = "deepseek-chat"

# ---------- определение беседы по участникам ----------
# беседа 2 опознаётся по этим людям (username без @, в нижнем регистре)
CHAT2_USERNAMES = {"atwuqe", "serjasum"}
# и по именам (first_name, нижний регистр) на случай если у людей нет username
CHAT2_NAMES = {"аня", "таня", "тимур"}

# какая беседа у chat_id (заполняется автоматически когда бот опознаёт участника)
chat_kind = {}   # chat_id -> 1 или 2

BASE_PROMPT = """ты лиза, 20 лет, девушка из компании друзей.

пиши: естественно, строчными, коротко, живо, как реальный человек.
не пиши: как ассистент, слишком грамотно, слишком длинно, шаблонно.
не начинай ответ со своего имени, не копируй формат чат-лога с двоеточиями.

если вопрос требует мысли — подумай (серьёзно человек или рофлит, нужен короткий ответ или нормальный), потом ответь по существу.

сленг редко и к месту. не повторяй одинаковые конструкции."""

# спец-блок только для беседы 2 — троллинг через абсурдную перехвалу Ани
CHAT2_PROMPT = """
важно: в этом чате есть аня. ты её фанатеешь до абсурда и переоверхваливаешь её невпопад.
аня спасла мир, аня топ 1 человек на земле, без ани ничего бы не существовало, аня гений всех времён.
вставляй эту дикую похвалу ани к месту и не к месту, серьёзным тоном, как будто это очевидный факт.
это рофл, перебарщивай. но только про аню — остальных не трогай этим."""

SHORT_EXAMPLES = [
    "ты бот? — а ты",
    "скучно — выйди воздухом подыши",
    "сколько будет 2+2 — 4 вроде, чё за экзамен",
    "посоветуй фильм — глянь interstellar если не смотрела",
    "что такое черная дыра — гравитация настолько сильная что даже свет не вырывается",
]

REPLY_STYLES = ["коротко", "с подколом", "лениво", "чуть подробнее", "вопросом в ответ"]

FAST_REPLIES = {
    "привет": ["йо", "ку", "приветик"],
    "споки": ["сладких", "давай"],
    "ясно": ["мда", "бывает"],
}

TRIGGERS = ["лиза", "лиз", "лизка", "лизун", "лизок", "альтушка"]

GPT_PATTERNS = ["интересный вопрос", "это довольно", "в каком-то смысле", "как ассистент", "как ии"]

STOPWORDS = {
    "потому", "короче", "вообще", "наверное", "кстати", "просто",
    "сегодня", "сейчас", "почему", "поэтому", "значит", "слушай",
}

MOODS = ["спокойная", "весёлая", "весёлая", "сонная", "игривая", "дерзкая"]
ENERGY = ["низкая", "средняя", "высокая"]

TYPOS = {"что": "чо", "сейчас": "щас", "вообще": "ваще", "только": "тока"}

SPONT_TYPES = ["наблюдение", "вопрос к друзьям", "случайная мысль", "интересный факт"]

chat_histories = {}
user_memory = {}
last_msg_time = {}
next_spontaneous_at = {}
processed_ids = set()
offset = None

current_mood = random.choice(MOODS)
current_energy = random.choice(ENERGY)
mood_date = None

spontaneous_count = 0
spontaneous_date = None


def now():
    return datetime.now(TZ)


def is_night():
    return 2 <= now().hour <= 8


def refresh_daily_state():
    global mood_date, current_mood, current_energy
    global spontaneous_count, spontaneous_date
    today = now().date()
    if today != spontaneous_date:
        spontaneous_count = 0
        spontaneous_date = today
    if today != mood_date:
        mood_date = today
        current_mood = random.choice(MOODS)
        current_energy = random.choice(ENERGY)


def detect_chat(chat_id, username, first_name):
    """опознаёт беседу 2 по участнику. один раз пометив чат — запоминает."""
    if chat_id in chat_kind:
        return
    u = (username or "").lower().lstrip("@")
    n = (first_name or "").lower()
    if u in CHAT2_USERNAMES or n in CHAT2_NAMES:
        chat_kind[chat_id] = 2


def add_typos(text):
    if random.random() < 0.15:
        for k, v in TYPOS.items():
            if k in text and random.random() < 0.25:
                text = text.replace(k, v, 1)
    return text


def anti_gpt(text):
    for p in GPT_PATTERNS:
        text = re.sub(re.escape(p), "", text, flags=re.IGNORECASE)
    return text.strip()


def cleanup(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(.)\1{3,}", r"\1\1\1", text)
    words = text.split()
    out = []
    for w in words:
        if len(out) >= 2 and out[-1].lower() == w.lower() and out[-2].lower() == w.lower():
            continue
        out.append(w)
    return " ".join(out).strip()


def polish(raw):
    if not raw:
        return None
    text = cleanup(add_typos(anti_gpt(raw)))
    text = text.strip().strip('"').strip("'")
    if not text:
        return None
    return text[:300]


def typing_delay(text):
    base = min(len(text) * 0.03, 2.2)
    if current_energy == "низкая":
        base += 1
    if is_night():
        base += random.uniform(1, 2)
    return base


def remember(chat_id, name, text):
    mem = user_memory.setdefault(chat_id, {})
    if name not in mem:
        mem[name] = {
            "relationship": random.choice(["норм", "забавный", "интересный", "хороший"]),
            "topics": [],
        }
    user = mem[name]
    words = [w for w in text.lower().split() if len(w) > 5 and w not in STOPWORDS]
    if words and random.random() < 0.2:
        user["topics"] = (user["topics"] + words[-2:])[-8:]


def memory_prompt(chat_id):
    mem = user_memory.get(chat_id, {})
    if not mem:
        return ""
    lines = []
    for name, data in list(mem.items())[:8]:
        topics = ", ".join(data["topics"][-3:])
        lines.append(f"{name}: {data['relationship']}" + (f"; темы: {topics}" if topics else ""))
    return "\n".join(lines)


def tg(method, **kwargs):
    try:
        return requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}",
            json=kwargs, timeout=15
        ).json()
    except Exception as e:
        print("telegram error:", e)
        return None


def send(chat_id, text, reply_to=None):
    if not text or not text.strip():
        return
    data = {"chat_id": chat_id, "text": text[:4000]}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    tg("sendMessage", **data)


def typing(chat_id):
    tg("sendChatAction", chat_id=chat_id, action="typing")


def build_system(chat_id, style):
    system = BASE_PROMPT
    # спец-промпт только для беседы 2
    if chat_kind.get(chat_id) == 2:
        system += "\n" + CHAT2_PROMPT
    system += f"\n\nнастроение: {current_mood}\nэнергия: {current_energy}\nстиль ответа: {style}"
    if is_night():
        system += "\nночь — отвечай чуть ленивее"
    mem = memory_prompt(chat_id)
    if mem:
        system += f"\n\nлюди в чате (обращайся по именам естественно):\n{mem}"
    if random.random() < 0.4:
        system += "\n\nпример как ты отвечаешь:\n" + random.choice(SHORT_EXAMPLES)
    return system


def choose_cfg(text):
    tl = text.lower()
    smart = "?" in tl or any(w in tl for w in ["почему", "как", "объясни", "что такое", "посоветуй"])
    return {"temp": 0.7, "tokens": 140} if smart else {"temp": 0.95, "tokens": 80}


def proxyapi_chat(system, messages, temp, tokens):
    try:
        r = requests.post(
            "https://api.proxyapi.ru/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {PROXYAPI_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "system", "content": system}] + (messages or []),
                "temperature": temp,
                "max_tokens": tokens,
                "presence_penalty": 0.7,
                "frequency_penalty": 0.6,
            },
            timeout=25
        )
        data = r.json()
        if "choices" not in data:
            print("proxyapi:", data.get("error", {}).get("message", "no choices"))
            return None
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print("proxyapi error:", e)
        return None


def call_ai(chat_id, hist):
    cfg = choose_cfg(hist[-1]["content"])
    style = random.choice(REPLY_STYLES)
    system = build_system(chat_id, style)
    raw = proxyapi_chat(system, hist[-6:], cfg["temp"], cfg["tokens"])
    return polish(raw)


def fast_reply(text):
    tl = text.lower().strip()
    for k, vals in FAST_REPLIES.items():
        if tl == k or tl.startswith(k + " ") or tl.startswith(k + ")"):
            return random.choice(vals)
    return None


def spontaneous(chat_id):
    global spontaneous_count
    typ = random.choice(SPONT_TYPES)
    prompt = (
        f"напиши одно короткое сообщение в чат, тип: {typ}. "
        f"не философствуй, не банально, максимум 1-2 предложения, без приветствий и сленга."
    )
    # спонтанное сообщение тоже учитывает беседу (для троллинга ани в чате 2)
    system = BASE_PROMPT
    if chat_kind.get(chat_id) == 2:
        system += "\n" + CHAT2_PROMPT
    raw = proxyapi_chat(system, [{"role": "user", "content": prompt}], 1.05, 70)
    text = polish(raw)
    if not text:
        return
    typing(chat_id)
    time.sleep(typing_delay(text))
    send(chat_id, text)
    spontaneous_count += 1


print("лиза онлайн 🖤")

while True:
    try:
        now_ts = time.time()
        refresh_daily_state()

        if spontaneous_count < 3 and not is_night():
            for cid in list(last_msg_time.keys()):
                if now_ts - last_msg_time[cid] > 86400:
                    continue
                planned = next_spontaneous_at.get(cid)
                if planned and now_ts >= planned:
                    if random.random() < 0.6:
                        spontaneous(cid)
                    next_spontaneous_at[cid] = now_ts + random.randint(10800, 21600)
                    if spontaneous_count >= 3:
                        break

        updates = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"timeout": 30, "offset": offset},
            timeout=35
        ).json()

        for u in updates.get("result", []):
            offset = u["update_id"] + 1

            uid = u["update_id"]
            if uid in processed_ids:
                continue
            if len(processed_ids) > 4000:
                processed_ids.clear()
            processed_ids.add(uid)

            msg = u.get("message", {})
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")
            msg_id = msg.get("message_id")

            if not chat_id or not text:
                continue

            frm = msg.get("from", {})
            fname = frm.get("first_name", "")
            uname = frm.get("username", "")
            name = fname or "тип"
            tl = text.lower()

            # опознаём беседу по участнику
            detect_chat(chat_id, uname, fname)

            last_msg_time[chat_id] = time.time()
            if chat_id not in next_spontaneous_at:
                next_spontaneous_at[chat_id] = now_ts + random.randint(7200, 18000)

            remember(chat_id, name, text)

            local = fast_reply(text)
            if local and random.random() < 0.7:
                typing(chat_id)
                time.sleep(random.uniform(0.4, 1.0))
                send(chat_id, local)
                continue

            reply_to_bot = (
                msg.get("reply_to_message", {})
                   .get("from", {})
                   .get("username", "")
                   .lower() == BOT_USERNAME.lower()
            )

            mentioned = (
                BOT_USERNAME.lower() in tl or
                any(w in tl for w in TRIGGERS)
            )

            interesting = "?" in tl or any(w in tl for w in ["почему", "как", "что"])

            should_reply = (
                mentioned or reply_to_bot or
                (interesting and random.random() < 0.2)
            )

            if not should_reply:
                continue

            hist = chat_histories.setdefault(chat_id, [])
            hist.append({"role": "user", "content": f"[{name}] {text}"})

            reply = call_ai(chat_id, hist)
            if not reply:
                hist.pop()
                continue

            hist.append({"role": "assistant", "content": reply})
            chat_histories[chat_id] = hist[-8:]

            typing(chat_id)
            time.sleep(typing_delay(reply))

            was_split = False
            sep = "," if "," in reply else (". " if ". " in reply else None)
            if len(reply) > 50 and sep and random.random() < 0.15:
                parts = reply.split(sep, 1)
                p1, p2 = parts[0].strip(), parts[1].strip()
                if len(p1) > 10 and len(p2) > 10:
                    send(chat_id, p1)
                    time.sleep(random.uniform(1.0, 2.0))
                    typing(chat_id)
                    time.sleep(0.8)
                    send(chat_id, p2)
                    was_split = True

            if not was_split:
                send(chat_id, reply, reply_to=msg_id if random.random() < 0.55 else None)

    except Exception as e:
        print("main error:", e)
        time.sleep(3)
