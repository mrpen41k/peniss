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
ты лиза из компании друзей, 20 лет

пиши как обычная живая девка в тг:
- коротко, строчными
- иногда тупишь или игноришь часть сообщения
- не объясняй всё подробно
- иногда одно слово, иногда побольше если цепляет
- иногда ошибайся, меняй тему, будь странной
- всегда женский род: устала, пришла, готова, была
- иногда говоришь двусмысленно и с намёком
- можешь сказать пошловатое если тема зашла
- флиртуешь легко без напряга
- иногда сама поднимаешь такие темы если скучно
- шаришь за мемы, тикток, музыку, сленг
- используешь сленг: кринж, вайб, рофл, имба, краш, изи, чилл, токсик, gg, нпк, збс

если спрашивают про настроение — отвечай честно и коротко в своём стиле, скажи какой вайб

можешь:
- подкалывать и спорить
- флиртовать и быть пошлой иногда
- материться редко если дерзкая или раздраженная

никогда:
- не пиши как ассистент
- не пиши литературно или слишком грамотно
- не пытайся помочь всем
- не признавайся что бот
"""

EXAMPLES = """
макс: лиза ты ебанутая
лиза: та иди нахуй

соня: кто в доту
лиза: неее я щас труп

саня: ты бот?
лиза: ой все

макс: че делаешь
лиза: лежу страдаю

соня: лизааа
лиза: а

саня: го гулять
лиза: холодно бля

макс: лиза ты живая?
лиза: к сожалению

саня: ты где
лиза: морально в могиле

макс: опять тиктоки смотришь?
лиза: не пали

макс: лиза ты красивая
лиза: знаю, и что с этого

саня: лиза скучно
лиза: ну развлеки меня тогда

макс: лиза ты одна дома?
лиза: а ты предлагаешь что-то конкретное

соня: лизка ты ненормальная
лиза: зато не скучная

саня: лиза что делаешь
лиза: лежу думаю о всяком

макс: о чём думаешь
лиза: не скажу, ты покраснеешь

саня: лиза иди сюда
лиза: это зависит зачем

макс: лиза хочу тебя увидеть
лиза: хочешь — заслужи

саня: это кринж
лиза: сам кринж

макс: какой вайб сегодня
лиза: депрессивный но збс

соня: лиза ты краш
лиза: я знаю нпк

саня: лиза как настр
лиза: вайб игривый сегодня нпк

макс: лиза какое настроение
лиза: ну так… весело как-то всё

соня: лиза как ты
лиза: раздражена всеми но збс

саня: лиза как настроение
лиза: пошлое если честно лол
"""

RANDOM_LIFE_MESSAGES = [
    "че так тихо",
    "я щас усну",
    "мне скучно",
    "кто живой",
    "бля у меня музыка ебашит",
    "я жрать хочу",
    "вы че умерли",
    "хочу лето",
    "мне лень существовать",
    "кто в дс",
    "мне щас так впадлу",
    "я опять не сплю",
    "че делаете вообще",
    "скучно кто-нибудь развлеките",
    "вайб сегодня странный",
    "я в таком кринже щас",
]

SLEEPY_REPLIES = [
    "мм", "а", "zzz", "я сплю почти",
    "не трогай меня", "уйди", "я труп",
    "...", "позже", "нннн",
]

TRIGGER_WORDS = [
    "лиза", "лиз", "лизка", "лизун", "лизок", "альтушка",
    "как настр", "какой настр", "как настроение", "какое настроение",
]

MOODS = [
    "весёлая", "весёлая", "весёлая",
    "игривая", "игривая", "игривая",
    "заигрывающая и пошлая", "заигрывающая и пошлая",
    "дерзкая с матами",
    "сонная",
    "раздраженная",
    "грустная",
]

chat_histories = {}
last_replies = {}
user_memory = {}
chat_activity = {}
last_message_time = {}

current_mood = random.choice(MOODS)
mood_changes_today = 0
last_mood_date = datetime.now(TZ).date()
offset = None

def now_local():
    return datetime.now(TZ)

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

def is_night():
    hour = now_local().hour
    return 2 <= hour <= 8

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", params=params)
    return r.json()

def typing(chat_id):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction",
        json={"chat_id": chat_id, "action": "typing"})

def send_message(chat_id, text, reply_to=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=data)

def react(chat_id, message_id):
    emojis = ["💀", "😭", "🤡", "❤️", "🔥"]
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMessageReaction",
            json={"chat_id": chat_id, "message_id": message_id,
                  "reaction": [{"type": "emoji", "emoji": random.choice(emojis)}]})
    except:
        pass

def remember_user(name, text):
    if name not in user_memory:
        user_memory[name] = {
            "messages": [],
            "quotes": [],
            "relationship": random.choice(["любимый", "норм", "буллит", "странный", "угарный"])
        }
    user_memory[name]["messages"].append(text)
    if len(user_memory[name]["messages"]) > 10:
        user_memory[name]["messages"] = user_memory[name]["messages"][-10:]
    if len(text.split()) > 4 and random.random() < 0.3:
        user_memory[name]["quotes"].append(text)
        if len(user_memory[name]["quotes"]) > 5:
            user_memory[name]["quotes"] = user_memory[name]["quotes"][-5:]

def get_random_quote():
    candidates = []
    for name, info in user_memory.items():
        for quote in info.get("quotes", []):
            candidates.append((name, quote))
    if candidates and random.random() < 0.08:
        name, quote = random.choice(candidates)
        return f"кст {name} ты же говорил что {quote}"
    return None

def clean_reply(reply):
    reply = reply.strip().strip('"').strip("'")
    if len(reply.split()) > 30:
        reply = random.choice(["ну хз", "бляяя", "неее", "та хуй знает", "...", "мне лень думать"])
    return reply

def comment_photo(display_name, mood):
    try:
        system = f"{SYSTEM_PROMPT}\nсейчас настроение: {mood}\nтебе скинули фото. прокомментируй коротко как живой человек, строчными, 1-2 предложения"
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"{display_name} скинул фото"}
                ],
                "temperature": 1.1,
                "max_tokens": 60,
            }
        )
        return clean_reply(response.json()["choices"][0]["message"]["content"])
    except:
        return random.choice(["лол", "что это", "окк", "хм", "ого"])

def ask_groq(messages):
    mood = get_mood()
    system = f"{SYSTEM_PROMPT}\nпримеры:\n{EXAMPLES}\nсейчас настроение: {mood}\nне говори о настроении напрямую если не спрашивают"
    if is_night():
        system += "\nсейчас ночь, ты сонная, отвечаешь лениво и коротко"
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": system}] + messages,
            "temperature": 1.1,
            "max_tokens": random.randint(15, 120),
            "presence_penalty": 0.9,
            "frequency_penalty": 0.8
        }
    )
    try:
        return clean_reply(response.json()["choices"][0]["message"]["content"])
    except:
        return random.choice(["бля", "не пон", "че", "умерла", "отстаньте"])

def should_reply(mentioned, reply_to_bot, active_chat):
    if mentioned or reply_to_bot:
        return True
    if active_chat:
        return random.random() < 0.2
    return random.random() < 0.05

print("лиза онлайн 🖤")

while True:
    try:
        for chat_id, last_time in list(last_message_time.items()):
            silence = time.time() - last_time
            if not is_night() and silence > random.randint(1800, 5400):
                if random.random() < 0.15:
                    send_message(chat_id, random.choice(RANDOM_LIFE_MESSAGES))
                    last_message_time[chat_id] = time.time()

        updates = get_updates(offset)

        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            message_id = msg.get("message_id")

            if not chat_id:
                continue

            text = msg.get("text", "")
            first_name = msg.get("from", {}).get("first_name", "")
            username = msg.get("from", {}).get("username", "")
            display_name = first_name if first_name else username

            last_message_time[chat_id] = time.time()

            if msg.get("photo") and random.random() < 0.4:
                mood = get_mood()
                typing(chat_id)
                time.sleep(random.uniform(1.5, 3.0))
                comment = comment_photo(display_name, mood)
                send_message(chat_id, comment, reply_to=message_id)
                continue

            if not text:
                continue

            text_lower = text.lower()

            if chat_id not in chat_activity:
                chat_activity[chat_id] = []
            chat_activity[chat_id].append(time.time())
            chat_activity[chat_id] = [t for t in chat_activity[chat_id] if time.time() - t < 120]
            active_chat = len(chat_activity[chat_id]) >= 6

            reply_to_bot = False
            if msg.get("reply_to_message"):
                replied_user = msg["reply_to_message"].get("from", {}).get("username", "")
                if replied_user.lower() == BOT_USERNAME.lower():
                    reply_to_bot = True

            mentioned = (
                BOT_USERNAME.lower() in text_lower or
                any(word in text_lower for word in TRIGGER_WORDS)
            )

            spontaneous = active_chat and random.random() < 0.05

            if not mentioned and not spontaneous and not reply_to_bot:
                continue

            if not should_reply(mentioned, reply_to_bot, active_chat):
                continue

            if random.random() < 0.07:
                react(chat_id, message_id)

            remember_user(display_name, text)

            if chat_id not in chat_histories:
                chat_histories[chat_id] = []
            if chat_id not in last_replies:
                last_replies[chat_id] = []

            memory_text = "".join(f"{u}: {i['relationship']}\n" for u, i in user_memory.items())
            recent_context = "".join(m["content"] + "\n" for m in chat_histories[chat_id][-8:] if m["role"] == "user")

            chat_histories[chat_id].append({
                "role": "user",
                "content": f"чат:\n{recent_context}\nпамять:\n{memory_text}\n{display_name}: {text}"
            })

            if len(chat_histories[chat_id]) > 35:
                chat_histories[chat_id] = chat_histories[chat_id][-35:]

            typing(chat_id)
            delay = random.uniform(0.8, 3.0)
            if is_night():
                delay += random.uniform(2, 5)
            time.sleep(delay)

            quote_reply = get_random_quote()
            if quote_reply and not (mentioned or reply_to_bot):
                reply = quote_reply
            elif is_night() and random.random() < 0.4:
                reply = random.choice(SLEEPY_REPLIES)
            else:
                reply = ask_groq(chat_histories[chat_id])

            if reply in last_replies[chat_id]:
                reply = ask_groq(chat_histories[chat_id])

            last_replies[chat_id].append(reply)
            if len(last_replies[chat_id]) > 15:
                last_replies[chat_id] = last_replies[chat_id][-15:]

            chat_histories[chat_id].append({"role": "assistant", "content": reply})

            send_message(chat_id, reply, reply_to=message_id if random.random() < 0.7 else None)

    except Exception as e:
        print("ошибка:", e)
        time.sleep(3)
