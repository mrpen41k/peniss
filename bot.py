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
ты лиза, 20 лет, из компании друзей

пиши как реальный человек в тг:
- коротко, строчными
- без умного стиля
- иногда тупишь, иногда игноришь часть фраз
- иногда одно слово, иногда 2-3 предложения если зацепило
- можешь спорить, подкалывать, флиртовать
- иногда грубая, иногда милая, иногда пофигистка
- всегда женский род: устала, пришла, готова
- иногда пошлая и двусмысленная
- используешь сленг: збс, нпк, кринж, вайб, ваще, щас, чо

никогда:
- не объясняй себя
- не говори как ассистент
- не признавайся что бот
"""

EXAMPLES = """
макс: лиза ты тупая
лиза: сам

соня: че делаешь
лиза: страдаю

саня: ты бот?
лиза: ага щас

макс: лиза скучно
лиза: ну придумай чё нибудь

соня: лиз
лиза: а

саня: ты где
лиза: тут

макс: лиза ты живая?
лиза: не уверена

саня: лиза как настр
лиза: вайб игривый нпк

макс: лиза что делаешь
лиза: лежу думаю о всяком

соня: о чём думаешь
лиза: не скажу покраснеешь

макс: лиза иди сюда
лиза: это зависит зачем

саня: лиза одна дома?
лиза: а ты предлагаешь чё конкретное
"""

TRIGGER_WORDS = [
    "лиза", "лиз", "лизка", "лизун", "лизок", "альтушка",
    "как настр", "какой настр", "как настроение",
]

MOODS = [
    "весёлая", "весёлая", "весёлая",
    "игривая", "игривая",
    "пошлая и заигрывающая", "пошлая и заигрывающая",
    "дерзкая",
    "сонная",
    "раздраженная",
    "грустная",
]

ACTIVITIES = [
    "лежу", "смотрю тиктоки", "страдаю",
    "ем", "ничего не делаю", "слушаю музыку", "в телефоне",
]

HORNY_WORDS = ["секс", "трах", "голая", "жопа", "хочу тебя", "пошл", "засос"]
TOXIC_WORDS = ["иди нахуй", "ебанутая", "долбаеб", "заткнись"]
FUNNY_WORDS = ["ахах", "ржу", "ору", "лол", "хахах"]

SLEEPY_REPLIES = ["мм", "а", "zzz", "не трогай", "уйди", "...", "позже"]

DOUBLE_MESSAGES = [
    ("бля", "я ток щас поняла"),
    ("подожди", "не так поняла"),
    ("ааа", "дошло наконец"),
    ("стоп", "это же про меня было"),
]

DELAYED_THOUGHTS = [
    "бля я ток щас поняла че {name} сказал",
    "кст {name} ты вообще думаешь когда пишешь",
    "всё думаю о том что {name} написал",
]

RANDOM_LIFE_MESSAGES = [
    "че так тихо",
    "мне скучно",
    "кто живой",
    "я жрать хочу",
    "хочу лето",
    "мне лень существовать",
    "вы все умерли чтоли",
    "скучно развлеките",
]

TYPOS = {
    "что": "чо", "сейчас": "щас", "тебя": "тя",
    "вообще": "ваще", "только": "тока", "ничего": "ничо",
}

current_mood = random.choice(MOODS)
current_activity = random.choice(ACTIVITIES)
mood_changes_today = 0
last_mood_date = datetime.now(TZ).date()

chat_histories = {}
user_memory = {}
chat_state = {}
last_message_time = {}
delayed_queue = []
offset = None

def now_local():
    return datetime.now(TZ)

def is_night():
    return 2 <= now_local().hour <= 8

def get_mood():
    global current_mood, mood_changes_today, last_mood_date
    today = now_local().date()
    if today != last_mood_date:
        mood_changes_today = 0
        last_mood_date = today
    if mood_changes_today < 3 and random.random() < 0.07:
        current_mood = random.choice(MOODS)
        mood_changes_today += 1
    return current_mood

def update_mood_from_text(text):
    global current_mood
    t = text.lower()
    if any(w in t for w in HORNY_WORDS):
        current_mood = "пошлая и заигрывающая"
    elif any(w in t for w in TOXIC_WORDS):
        current_mood = "раздраженная"
    elif any(w in t for w in FUNNY_WORDS):
        current_mood = "весёлая"

def get_state(chat_id):
    if chat_id not in chat_state:
        chat_state[chat_id] = {"energy": random.uniform(0.4, 0.8)}
    return chat_state[chat_id]

def update_state(chat_id):
    s = get_state(chat_id)
    if random.random() < 0.1:
        s["energy"] += random.uniform(-0.1, 0.1)
    s["energy"] = max(0.1, min(1.0, s["energy"]))

def remember(chat_id, name, text):
    if chat_id not in user_memory:
        user_memory[chat_id] = {}
    if name not in user_memory[chat_id]:
        user_memory[chat_id][name] = {
            "quotes": [], "trust": 0.5, "flirt": 0.0,
            "relationship": random.choice(["норм", "угарный", "странный", "любимый"])
        }
    u = user_memory[chat_id][name]
    if len(text.split()) > 4 and random.random() < 0.3:
        u["quotes"].append(text)
        u["quotes"] = u["quotes"][-5:]
    t = text.lower()
    if any(w in t for w in TOXIC_WORDS):
        u["trust"] -= 0.05
    if any(w in t for w in ["люб", "красив", "нрав"]):
        u["flirt"] += 0.1
        u["trust"] += 0.05
    u["trust"] = max(0, min(1, u["trust"]))
    if random.random() < 0.1:
        u["relationship"] = random.choice(["норм", "угарный", "странный"])

def get_quote():
    all_quotes = []
    for chat in user_memory.values():
        for name, data in chat.items():
            for q in data.get("quotes", []):
                all_quotes.append((name, q))
    if all_quotes and random.random() < 0.07:
        name, q = random.choice(all_quotes)
        return f"кст {name} ты же говорил что {q}"
    return None

def add_typos(text):
    if random.random() < 0.3:
        for k, v in TYPOS.items():
            if k in text and random.random() < 0.4:
                text = text.replace(k, v, 1)
    return text

def build_memory_str(chat_id):
    result = ""
    for name, data in user_memory.get(chat_id, {}).items():
        result += f"{name}: {data['relationship']}, trust={data['trust']:.1f}\n"
    return result

def typing(chat_id):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"})
    except:
        pass

def send(chat_id, text, reply_to=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=data)
    except:
        pass

def react(chat_id, msg_id):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMessageReaction",
            json={"chat_id": chat_id, "message_id": msg_id,
                  "reaction": [{"type": "emoji", "emoji": random.choice(["💀","😭","🔥","🤡","❤️"])}]})
    except:
        pass

def comment_photo(display_name):
    try:
        mood = get_mood()
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": f"{SYSTEM_PROMPT}\nнастроение: {mood}\nпрокомментируй фото коротко, 1 предложение, строчными"},
                    {"role": "user", "content": f"{display_name} скинул фото"}
                ],
                "temperature": 1.1, "max_tokens": 50
            }
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return random.choice(["лол", "окк", "хм", "ого"])

def ask_groq(chat_id, messages):
    mood = get_mood()
    state = get_state(chat_id)
    system = f"{SYSTEM_PROMPT}\nпримеры:\n{EXAMPLES}\nнастроение: {mood}\nзанята: {current_activity}\nэнергия: {state['energy']:.1f}\nне говори об этом напрямую"
    if is_night():
        system += "\nночь, ты сонная, пиши лениво и коротко"
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": system}] + messages,
                "temperature": 1.1,
                "max_tokens": random.randint(15, 100),
                "presence_penalty": 0.9,
                "frequency_penalty": 0.8
            }
        )
        reply = r.json()["choices"][0]["message"]["content"].strip()
        if len(reply.split()) > 30:
            reply = random.choice(["ну хз", "бля", "неее", "мне лень"])
        return reply
    except:
        return random.choice(["бля", "не пон", "че", "отстаньте"])

def should_reply(chat_id, mentioned, reply_to_bot):
    if mentioned or reply_to_bot:
        return True
    state = get_state(chat_id)
    return random.random() < (0.05 + state["energy"] * 0.15)

print("лиза онлайн 🖤")

while True:
    try:
        # отложенные мысли
        for thought in delayed_queue[:]:
            if time.time() >= thought["send_at"]:
                send(thought["chat_id"], thought["text"])
                delayed_queue.remove(thought)

        # сама пишет если тихо
        for chat_id, last_t in list(last_message_time.items()):
            if not is_night() and time.time() - last_t > random.randint(1800, 5400):
                if random.random() < 0.12:
                    if random.random() < 0.3:
                        send(chat_id, f"я {current_activity} кст")
                    else:
                        send(chat_id, random.choice(RANDOM_LIFE_MESSAGES))
                    last_message_time[chat_id] = time.time()

        updates = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"timeout": 30, "offset": offset}
        ).json()

        for u in updates.get("result", []):
            offset = u["update_id"] + 1
            msg = u.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            msg_id = msg.get("message_id")

            if not chat_id:
                continue

            text = msg.get("text", "")
            first_name = msg.get("from", {}).get("first_name", "")
            username = msg.get("from", {}).get("username", "")
            display_name = first_name if first_name else username

            last_message_time[chat_id] = time.time()
            update_state(chat_id)

            # фото
            if msg.get("photo") and random.random() < 0.35:
                typing(chat_id)
                time.sleep(random.uniform(1.5, 3.0))
                send(chat_id, comment_photo(display_name), reply_to=msg_id)
                continue

            if not text:
                continue

            update_mood_from_text(text)
            remember(chat_id, display_name, text)

            text_lower = text.lower()

            reply_to_bot = False
            if msg.get("reply_to_message"):
                ru = msg["reply_to_message"].get("from", {}).get("username", "")
                if ru.lower() == BOT_USERNAME.lower():
                    reply_to_bot = True

            mentioned = (
                BOT_USERNAME.lower() in text_lower or
                any(w in text_lower for w in TRIGGER_WORDS)
            )

            if not mentioned and not reply_to_bot and random.random() > 0.08:
                # иногда просто реагирует
                if random.random() < 0.05:
                    react(chat_id, msg_id)
                continue

            if not should_reply(chat_id, mentioned, reply_to_bot):
                if random.random() < 0.25:
                    react(chat_id, msg_id)
                continue

            if random.random() < 0.06:
                react(chat_id, msg_id)

            chat_histories.setdefault(chat_id, [])
            mem_str = build_memory_str(chat_id)
            recent = "".join(m["content"] + "\n" for m in chat_histories[chat_id][-6:] if m["role"] == "user")

            chat_histories[chat_id].append({
                "role": "user",
                "content": f"чат:\n{recent}\nпамять:\n{mem_str}\n{display_name}: {text}"
            })
            chat_histories[chat_id] = chat_histories[chat_id][-30:]

            typing(chat_id)
            delay = random.uniform(0.8, 2.5)
            if is_night():
                delay += random.uniform(2, 4)
            time.sleep(delay)

            # выбор ответа
            quote = get_quote()
            if quote and not (mentioned or reply_to_bot) and random.random() < 0.4:
                reply = quote
            elif is_night() and random.random() < 0.35:
                reply = random.choice(SLEEPY_REPLIES)
            else:
                reply = ask_groq(chat_id, chat_histories[chat_id])
                reply = add_typos(reply)

            chat_histories[chat_id].append({"role": "assistant", "content": reply})

            # двойное сообщение
            if random.random() < 0.07:
                first, second = random.choice(DOUBLE_MESSAGES)
                send(chat_id, first)
                time.sleep(random.uniform(1.0, 2.0))
                typing(chat_id)
                time.sleep(1.0)
                send(chat_id, second)
            else:
                send(chat_id, reply, reply_to=msg_id if random.random() < 0.65 else None)

            # отложенная мысль
            if user_memory.get(chat_id) and random.random() < 0.05:
                name = random.choice(list(user_memory[chat_id].keys()))
                thought = random.choice(DELAYED_THOUGHTS).format(name=name)
                delayed_queue.append({
                    "chat_id": chat_id,
                    "text": thought,
                    "send_at": time.time() + random.randint(300, 1200)
                })

    except Exception as e:
        print("ошибка:", e)
        time.sleep(3)
