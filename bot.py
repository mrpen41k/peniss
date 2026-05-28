import os
import time
import random
import requests
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

BOT_USERNAME = "RbIjbIK_bot"
TZ = timezone(timedelta(hours=5))

SYSTEM_PROMPT = """ты лиза, 20 лет, девчонка в групповом чате.
пиши ТОЛЬКО строчными, коротко, в женском роде (пришла, поняла).
стиль: живая, игривая, дерзкая, иногда пошлая.
сленг: збс, кринж, вайб, ваще, щас, чо, ток, хз.
если не знаешь тему: "не шарю", "чо это".
НИКОГДА не пиши как ассистент, не начинай с "лиза:"."""

EXAMPLES = """макс: лиза ты тупая
лиза: сам
соня: че делаешь
лиза: лежу страдаю
саня: ты бот?
лиза: серьёзно чтоли
лиза о чём думаешь
лиза: не скажу покраснеешь
лиза одна дома?
лиза: а ты предлагаешь чё конкретное
лиза не знаешь этого?
лиза: не шарю ваще объясни
лиза скучно
лиза: сам придумай
макс: лиза иди нахуй
лиза: сам иди"""

TRIGGER_WORDS = [
    "лиза", "лиз", "лизка", "лизун", "лизок", "альтушка",
    "как настр", "какой настр", "как настроение",
]

MOODS = [
    "весёлая", "весёлая", "весёлая",
    "игривая", "игривая",
    "пошлая и заигрывающая", "пошлая и заигрывающая",
    "дерзкая", "сонная", "раздраженная", "грустная",
]

ACTIVITIES = [
    "лежу", "смотрю тиктоки", "страдаю",
    "ем", "ничего не делаю", "слушаю музыку",
]

HORNY_WORDS = ["секс", "трах", "голая", "жопа", "хочу тебя", "пошл", "засос"]
TOXIC_WORDS = ["иди нахуй", "ебанутая", "долбаеб", "заткнись"]
FUNNY_WORDS = ["ахах", "ржу", "ору", "лол", "хахах"]

SLEEPY = ["мм", "а", "уйди", "...", "позже", "zzz"]

DELAYED = [
    "бля я ток щас поняла че {name} сказал",
    "кст {name} ты вообще думаешь когда пишешь",
    "всё думаю про то что {name} написал",
]

# промпт для генерации спонтанного сообщения (интересного)
SPONTANEOUS_PROMPT = """придумай ОДНО короткое сообщение в чат от себя, строчными, как живая девка.
это может быть: интересный факт, мысль вслух, наблюдение, что-то про погоду/настроение/жизнь, рандомный вопрос к чату.
не банальное "мне скучно", а что-то цепляющее или смешное.
максимум 1-2 предложения. без приветствий."""

TYPOS = {
    "что": "чо", "сейчас": "щас",
    "вообще": "ваще", "только": "тока", "ничего": "ничо",
}

MATS = ["бля", "ну нахуй", "сука", "ёпта"]

current_mood = random.choice(MOODS)
current_activity = random.choice(ACTIVITIES)
mood_changes = 0
last_mood_date = None

chat_histories = {}
user_memory = {}
last_msg_time = {}
delayed_queue = []
offset = None

# контроль спонтанных сообщений: счётчик за день и время следующего
spontaneous_count = 0
spontaneous_date = None
next_spontaneous_at = {}

def now():
    return datetime.now(TZ)

def is_night():
    return 2 <= now().hour <= 8

def get_mood():
    global current_mood, mood_changes, last_mood_date
    today = now().date()
    if today != last_mood_date:
        mood_changes = 0
        last_mood_date = today
    if mood_changes < 3 and random.random() < 0.07:
        current_mood = random.choice(MOODS)
        mood_changes += 1
    return current_mood

def update_mood(text):
    global current_mood
    t = text.lower()
    if any(w in t for w in HORNY_WORDS):
        current_mood = "пошлая и заигрывающая"
    elif any(w in t for w in TOXIC_WORDS):
        current_mood = "раздраженная"
    elif any(w in t for w in FUNNY_WORDS):
        current_mood = "весёлая"

def remember(chat_id, name, text):
    mem = user_memory.setdefault(chat_id, {})
    if name not in mem:
        mem[name] = {
            "quotes": [],
            "rel": random.choice(["норм", "угарный", "странный", "любимый"])
        }
    u = mem[name]
    if len(text.split()) > 4 and random.random() < 0.3:
        u["quotes"] = (u["quotes"] + [text])[-3:]
    if random.random() < 0.1:
        u["rel"] = random.choice(["норм", "угарный", "странный"])

def get_quote():
    all_q = [(n, q) for cd in user_memory.values()
             for n, d in cd.items() for q in d.get("quotes", [])]
    if all_q and random.random() < 0.05:
        name, q = random.choice(all_q)
        return f"кст {name} ты же говорил что {q}"
    return None

def mem_str(chat_id):
    return "".join(
        f"{n}: {d['rel']}\n"
        for n, d in user_memory.get(chat_id, {}).items()
    )

def add_typos(text):
    if random.random() < 0.25:
        for k, v in TYPOS.items():
            if k in text and random.random() < 0.4:
                text = text.replace(k, v, 1)
    return text

def maybe_mat(text):
    if random.random() < 0.2:
        mat = random.choice(MATS)
        text = (mat + " " + text) if random.random() < 0.5 else (text + " " + mat)
    return text

def tg(method, **kwargs):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}",
            json=kwargs, timeout=10
        )
    except:
        pass

def send(chat_id, text, reply_to=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    tg("sendMessage", **data)

def typing(chat_id):
    tg("sendChatAction", chat_id=chat_id, action="typing")

def react(chat_id, msg_id):
    tg("setMessageReaction", chat_id=chat_id, message_id=msg_id,
       reaction=[{"type": "emoji", "emoji": random.choice(["💀","😭","🔥","🤡","❤️"])}])

def call_groq(messages, system):
    try:
        payload_messages = [{"role": "system", "content": system}] + (messages or [])
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": payload_messages,
                "temperature": 1.1,
                "max_tokens": random.randint(30, 70),
                "presence_penalty": 0.9,
                "frequency_penalty": 0.8,
            },
            timeout=20
        )
        data = r.json()
        if "choices" not in data:
            print("groq:", data.get("error", {}).get("message", "no choices"))
            return None
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("groq error:", e)
        return None

def ask(chat_id, messages):
    mood = get_mood()
    memory_data = mem_str(chat_id)
    system_parts = [
        SYSTEM_PROMPT,
        f"настроение: {mood}",
        f"занята: {current_activity}",
    ]
    if memory_data:
        system_parts.append(f"отношение к людям:\n{memory_data.strip()}")
    if is_night():
        system_parts.append("ночь — пиши сонно и лениво")
    system_parts.append(EXAMPLES)
    system = "\n\n".join(system_parts)
    return call_groq(messages=messages, system=system)

def make_spontaneous():
    mood = get_mood()
    system = f"{SYSTEM_PROMPT}\n\nнастроение: {mood}\n\n{SPONTANEOUS_PROMPT}"
    reply = call_groq(messages=[{"role": "user", "content": "напиши сообщение в чат"}], system=system)
    if reply:
        reply = add_typos(reply)
    return reply

def reset_spontaneous_if_new_day():
    global spontaneous_count, spontaneous_date
    today = now().date()
    if today != spontaneous_date:
        spontaneous_count = 0
        spontaneous_date = today
        # сбрасываем расписание для всех чатов
        for cid in list(next_spontaneous_at.keys()):
            next_spontaneous_at[cid] = None

print("лиза онлайн 🖤")

while True:
    try:
        now_ts = time.time()
        reset_spontaneous_if_new_day()

        # отложенные мысли
        for t in delayed_queue[:]:
            if now_ts >= t["at"]:
                send(t["chat_id"], t["text"])
                delayed_queue.remove(t)

        # спонтанные сообщения — максимум 3 в день на чат, днём, с большими промежутками
        if spontaneous_count < 3 and not is_night():
            for cid in list(last_msg_time.keys()):
                planned = next_spontaneous_at.get(cid)
                # если ещё не запланировано — ставим случайное время через 2-5 часов
                if planned is None:
                    next_spontaneous_at[cid] = now_ts + random.randint(7200, 18000)
                    continue
                if now_ts >= planned:
                    msg = make_spontaneous()
                    if msg:
                        typing(cid)
                        time.sleep(random.uniform(1.5, 3.0))
                        send(cid, msg)
                        spontaneous_count += 1
                    # планируем следующее через 3-6 часов
                    next_spontaneous_at[cid] = now_ts + random.randint(10800, 21600)

        updates = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"timeout": 30, "offset": offset},
            timeout=35
        ).json()

        for u in updates.get("result", []):
            offset = u["update_id"] + 1
            msg = u.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            msg_id = msg.get("message_id")

            if not chat_id:
                continue

            text = msg.get("text", "")
            fname = msg.get("from", {}).get("first_name", "")
            uname = msg.get("from", {}).get("username", "")
            name = fname or uname

            last_msg_time[chat_id] = time.time()
            # регистрируем чат для спонтанных сообщений
            if chat_id not in next_spontaneous_at:
                next_spontaneous_at[chat_id] = None

            if not text:
                if msg.get("photo") and random.random() < 0.3:
                    react(chat_id, msg_id)
                continue

            update_mood(text)
            remember(chat_id, name, text)

            tl = text.lower()

            reply_to_bot = (
                msg.get("reply_to_message", {})
                   .get("from", {})
                   .get("username", "")
                   .lower() == BOT_USERNAME.lower()
            )

            mentioned = (
                BOT_USERNAME.lower() in tl or
                any(w in tl for w in TRIGGER_WORDS)
            )

            if not mentioned and not reply_to_bot:
                if random.random() < 0.03:
                    react(chat_id, msg_id)
                if random.random() > 0.05:
                    continue

            if not (mentioned or reply_to_bot) and random.random() > 0.25:
                if random.random() < 0.15:
                    react(chat_id, msg_id)
                continue

            if random.random() < 0.05:
                react(chat_id, msg_id)

            hist = chat_histories.setdefault(chat_id, [])
            hist.append({"role": "user", "content": f"{name}: {text}"})

            if is_night() and random.random() < 0.3:
                reply = random.choice(SLEEPY)
                time.sleep(random.uniform(1.5, 3.0))
            else:
                q = get_quote()
                if q and not (mentioned or reply_to_bot) and random.random() < 0.05:
                    reply = q
                    typing(chat_id)
                    time.sleep(random.uniform(0.5, 1.2))
                    reply = add_typos(reply)
                    reply = maybe_mat(reply)
                else:
                    typing(chat_id)
                    time.sleep(random.uniform(0.8, 2.2) + (random.uniform(2, 4) if is_night() else 0))
                    reply = ask(chat_id, hist[-6:])
                    if reply is None:
                        continue
                    reply = add_typos(reply)
                    reply = maybe_mat(reply)

            hist.append({"role": "assistant", "content": reply})
            chat_histories[chat_id] = hist[-6:]

            was_split = False
            if len(reply) > 35 and ',' in reply and random.random() < 0.18:
                parts = reply.split(',', 1)
                if len(parts[0]) > 8 and len(parts[1]) > 8:
                    send(chat_id, parts[0].strip())
                    time.sleep(random.uniform(1.2, 2.5))
                    typing(chat_id)
                    time.sleep(0.8)
                    send(chat_id, parts[1].strip())
                    was_split = True

            if not was_split:
                send(chat_id, reply, reply_to=msg_id if random.random() < 0.65 else None)

            if user_memory.get(chat_id) and random.random() < 0.04:
                n = random.choice(list(user_memory[chat_id].keys()))
                delayed_queue.append({
                    "chat_id": chat_id,
                    "text": random.choice(DELAYED).format(name=n),
                    "at": time.time() + random.randint(300, 1200)
                })

    except Exception as e:
        print("ошибка:", e)
        time.sleep(3)
