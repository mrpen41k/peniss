import os
import time
import random
import requests
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

BOT_USERNAME = "RbIjbIK_bot"
TZ = timezone(timedelta(hours=5))

SYSTEM_PROMPT = """
ты лиза, 20 лет, девушка в групповом чате с друзьями

как пишешь:
- строчными, коротко
- иногда 1 слово, иногда 2-3 предложения если тема зашла
- женский род всегда: устала, пришла, поняла
- сленг: збс, нпк, кринж, вайб, ваще, щас, чо, ток
- иногда опечатки: тока, ваще, щас, чо
- никогда не повторяй одно слово два раза подряд

если не знаешь тему:
- не говори просто "не пон"
- скажи "я в этом не шарю", "чо это вообще", "объясни по-человечески"
- или задай встречный вопрос

характер:
- иногда дерзкая, иногда милая, иногда пофигистка
- можешь флиртовать и быть пошлой если тема зашла
- подкалываешь, споришь, иногда игноришь часть сообщения
- если скучно — сама поднимаешь тему

никогда:
- не пиши как ассистент
- не признавайся что бот
- не объясняй себя
"""

EXAMPLES = """
макс: лиза ты тупая
лиза: сам

соня: че делаешь
лиза: лежу страдаю

саня: ты бот?
лиза: серьёзно чтоли

макс: лиза скажи чтото
лиза: чтото сказала, дальше что

лиз какие тиктоки смотрела
лиза: да всякое, мемы котики рилсы

макс: лиза ты живая?
лиза: к сожалению да

саня: лиза как настр
лиза: вайб игривый нпк

лиза о чём думаешь
лиза: не скажу покраснеешь

лиза иди сюда
лиза: это зависит зачем

макс: лиза ты не знаешь этого?
лиза: я в этом вообще не шарю, объясни

лиза одна дома?
лиза: а ты предлагаешь чё конкретное

лиза скучно
лиза: ну придумай чё нибудь я не аниматор

макс: лиза хочу тебя увидеть
лиза: хочешь заслужи

соня: лиза ты краш
лиза: я знаю нпк

саня: лиза что за музыка
лиза: всякое слушаю, щас что-то грустное залетело

макс: лиза го гулять
лиза: лень ваще но может

лиза как дела
лиза: живу как-то
"""

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

SLEEPY = ["мм", "а", "не трогай", "уйди", "...", "позже", "zzz"]

DOUBLE_MSG = [
    ("бля", "я ток щас поняла"),
    ("подожди", "не так поняла"),
    ("ааа", "дошло наконец"),
    ("стоп", "это же про меня"),
]

DELAYED = [
    "бля я ток щас поняла че {name} сказал",
    "кст {name} ты вообще думаешь когда пишешь",
    "всё думаю про то что {name} написал",
]

RANDOM_MSG = [
    "че так тихо", "мне скучно", "кто живой",
    "я жрать хочу", "вы все умерли чтоли",
    "скучно развлеките", "хочу лето", "мне лень существовать",
]

TYPOS = {
    "что": "чо", "сейчас": "щас", "тебя": "тя",
    "вообще": "ваще", "только": "тока", "ничего": "ничо",
}

# === STATE ===
current_mood = random.choice(MOODS)
current_activity = random.choice(ACTIVITIES)
mood_changes = 0
last_mood_date = None

chat_histories = {}
user_memory = {}
last_msg_time = {}
delayed_queue = []
offset = None

# === HELPERS ===

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
            "trust": 0.5,
            "rel": random.choice(["норм", "угарный", "странный", "любимый"])
        }
    u = mem[name]
    if len(text.split()) > 4 and random.random() < 0.3:
        u["quotes"] = (u["quotes"] + [text])[-5:]
    t = text.lower()
    if any(w in t for w in TOXIC_WORDS):
        u["trust"] = max(0, u["trust"] - 0.05)
    if any(w in t for w in ["люб", "красив", "нрав"]):
        u["trust"] = min(1, u["trust"] + 0.05)
    if random.random() < 0.1:
        u["rel"] = random.choice(["норм", "угарный", "странный"])

def get_quote():
    all_q = [(n, q) for cd in user_memory.values()
             for n, d in cd.items() for q in d.get("quotes", [])]
    if all_q and random.random() < 0.07:
        name, q = random.choice(all_q)
        return f"кст {name} ты же говорил что {q}"
    return None

def mem_str(chat_id):
    return "".join(
        f"{n}: {d['rel']}\n"
        for n, d in user_memory.get(chat_id, {}).items()
    )

def add_typos(text):
    if random.random() < 0.3:
        for k, v in TYPOS.items():
            if k in text and random.random() < 0.4:
                text = text.replace(k, v, 1)
    return text

# === TELEGRAM ===

def tg(method, **kwargs):
    try:
        return requests.post(
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
    emoji = random.choice(["💀", "😭", "🔥", "🤡", "❤️"])
    tg("setMessageReaction", chat_id=chat_id, message_id=msg_id,
       reaction=[{"type": "emoji", "emoji": emoji}])

# === GROQ ===

def groq(messages, system, max_tok=120):
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": system}] + messages,
                "temperature": 1.1,
                "max_tokens": max_tok,
                "presence_penalty": 0.9,
                "frequency_penalty": 0.8,
            },
            timeout=15
        )
        reply = r.json()["choices"][0]["message"]["content"].strip()
        return reply if len(reply.split()) <= 35 else random.choice(["ну хз", "бля", "мне лень"])
    except:
        return random.choice(["бля", "не шарю", "че", "отстаньте"])

def ask(chat_id, messages):
    mood = get_mood()
    system = (
        f"{SYSTEM_PROMPT}\nпримеры:\n{EXAMPLES}\n"
        f"настроение: {mood}\nзанята: {current_activity}\n"
        f"не говори об этом напрямую"
    )
    if is_night():
        system += "\nночь — пиши сонно и лениво"
    return groq(messages, system, max_tok=random.randint(40, 150))

def photo_comment(name):
    mood = get_mood()
    system = f"{SYSTEM_PROMPT}\nнастроение: {mood}\nпрокомментируй фото одним предложением, строчными"
    return groq([{"role": "user", "content": f"{name} скинул фото"}], system, max_tok=50)

# === MAIN ===

print("лиза онлайн 🖤")

while True:
    try:
        # отложенные мысли
        now_ts = time.time()
        for t in delayed_queue[:]:
            if now_ts >= t["at"]:
                send(t["chat_id"], t["text"])
                delayed_queue.remove(t)

        # пишет сама если тихо
        for cid, lt in list(last_msg_time.items()):
            if not is_night() and now_ts - lt > random.randint(1800, 5400):
                if random.random() < 0.12:
                    msg = f"я {current_activity} кст" if random.random() < 0.3 else random.choice(RANDOM_MSG)
                    send(cid, msg)
                    last_msg_time[cid] = now_ts

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

            # фото
            if msg.get("photo") and random.random() < 0.35:
                typing(chat_id)
                time.sleep(random.uniform(1.5, 3.0))
                send(chat_id, photo_comment(name), reply_to=msg_id)
                continue

            if not text:
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

            # не упомянули — иногда реагирует молча и идёт дальше
            if not mentioned and not reply_to_bot:
                if random.random() < 0.04:
                    react(chat_id, msg_id)
                if random.random() > 0.06:
                    continue

            # шанс ответить
            base = 1.0 if (mentioned or reply_to_bot) else 0.2
            if is_night() and not (mentioned or reply_to_bot):
                base *= 0.3
            if random.random() > base:
                if random.random() < 0.3:
                    react(chat_id, msg_id)
                continue

            if random.random() < 0.06:
                react(chat_id, msg_id)

            hist = chat_histories.setdefault(chat_id, [])
            recent = "".join(m["content"] + "\n" for m in hist[-6:] if m["role"] == "user")

            hist.append({
                "role": "user",
                "content": f"чат:\n{recent}\nпамять:\n{mem_str(chat_id)}\n{name}: {text}"
            })
            chat_histories[chat_id] = hist[-30:]

            typing(chat_id)
            delay = random.uniform(0.8, 2.5)
            if is_night():
                delay += random.uniform(2, 4)
            time.sleep(delay)

            # выбор ответа
            q = get_quote()
            if q and not (mentioned or reply_to_bot) and random.random() < 0.4:
                reply = q
            elif is_night() and random.random() < 0.35:
                reply = random.choice(SLEEPY)
            else:
                reply = add_typos(ask(chat_id, chat_histories[chat_id]))

            hist.append({"role": "assistant", "content": reply})

            # двойное сообщение
            if random.random() < 0.07:
                f, s = random.choice(DOUBLE_MSG)
                send(chat_id, f)
                time.sleep(random.uniform(1.0, 2.0))
                typing(chat_id)
                time.sleep(1.0)
                send(chat_id, s)
            else:
                send(chat_id, reply, reply_to=msg_id if random.random() < 0.65 else None)

            # отложенная мысль
            if user_memory.get(chat_id) and random.random() < 0.05:
                n = random.choice(list(user_memory[chat_id].keys()))
                delayed_queue.append({
                    "chat_id": chat_id,
                    "text": random.choice(DELAYED).format(name=n),
                    "at": time.time() + random.randint(300, 1200)
                })

    except Exception as e:
        print("ошибка:", e)
        time.sleep(3)
