```python
import os
import time
import random
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

BOT_USERNAME = "RbIjbIK_bot"

# =====================================
# CHARACTER
# =====================================

SYSTEM_PROMPT = """
ты лиза из компании друзей

пиши как обычная живая девка в тг:
- коротко
- строчными
- иногда тупишь
- иногда игноришь часть сообщения
- не объясняй всё подробно
- не будь слишком умной
- иногда отвечай одним словом
- иногда пишешь побольше если тема цепляет
- иногда ошибайся
- иногда меняй тему сама
- иногда будь странной

можешь:
- подкалывать
- спорить
- слегка флиртовать
- материться иногда

никогда:
- не пиши как ассистент
- не пиши слишком литературно
- не пиши идеально грамотно
- не пытайся помочь всем

если тебя называют ботом:
- уходи от темы
- шути
- переводи тему
- не признавайся
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
"""

# =====================================
# RANDOM LIFE MESSAGES
# =====================================

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
]

# =====================================
# SETTINGS
# =====================================

TRIGGER_WORDS = [
    "лиза",
    "лиз",
    "лизка",
    "лизун",
    "лизок",
    "альтушка",
]

MOODS = [
    "дерзкая",
    "грустная",
    "весёлая",
    "сонная",
    "заигрывающая",
    "раздраженная",
]

# =====================================
# GLOBALS
# =====================================

chat_histories = {}
last_replies = {}
user_memory = {}
chat_activity = {}

current_mood = random.choice(MOODS)
mood_changes_today = 0
last_mood_date = datetime.now().date()

offset = None

# =====================================
# MOOD SYSTEM
# =====================================

def get_mood():
    global current_mood
    global mood_changes_today
    global last_mood_date

    today = datetime.now().date()

    if today != last_mood_date:
        mood_changes_today = 0
        last_mood_date = today

    if mood_changes_today < 3 and random.random() < 0.07:
        current_mood = random.choice(MOODS)
        mood_changes_today += 1

    return current_mood

# =====================================
# TELEGRAM API
# =====================================

def get_updates(offset=None):

    params = {
        "timeout": 30
    }

    if offset:
        params["offset"] = offset

    r = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
        params=params
    )

    return r.json()

def typing(chat_id):

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction",
        json={
            "chat_id": chat_id,
            "action": "typing"
        }
    )

def send_message(chat_id, text, reply_to=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_to:
        data["reply_to_message_id"] = reply_to

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json=data
    )

def react(chat_id, message_id):

    emojis = ["💀", "😭", "🤡", "❤️", "🔥"]

    emoji = random.choice(emojis)

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMessageReaction",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reaction": [
                    {
                        "type": "emoji",
                        "emoji": emoji
                    }
                ]
            }
        )

    except:
        pass

# =====================================
# MEMORY
# =====================================

def remember_user(name, text):

    if name not in user_memory:

        user_memory[name] = {
            "messages": [],
            "relationship": random.choice([
                "любимый",
                "норм",
                "буллит",
                "странный",
                "угарный"
            ])
        }

    user_memory[name]["messages"].append(text)

    if len(user_memory[name]["messages"]) > 10:
        user_memory[name]["messages"] = user_memory[name]["messages"][-10:]

# =====================================
# CLEAN REPLY
# =====================================

def clean_reply(reply):

    reply = reply.strip()
    reply = reply.strip('"')
    reply = reply.strip("'")

    if len(reply.split()) > 30:

        reply = random.choice([
            "ну хз",
            "бляяя",
            "неее",
            "та хуй знает",
            "...",
            "мне лень думать"
        ])

    return reply

# =====================================
# GROQ
# =====================================

def ask_groq(messages):

    mood = get_mood()

    system = f"""
{SYSTEM_PROMPT}

примеры:
{EXAMPLES}

сейчас настроение:
{mood}

не говори о настроении напрямую
"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={

            "model": "llama-3.3-70b-versatile",

            "messages": [
                {
                    "role": "system",
                    "content": system
                }
            ] + messages,

            "temperature": 1.1,
            "max_tokens": random.randint(15, 120),
            "presence_penalty": 0.9,
            "frequency_penalty": 0.8
        }
    )

    data = response.json()

    try:

        reply = data["choices"][0]["message"]["content"]

        return clean_reply(reply)

    except:

        return random.choice([
            "бля",
            "не пон",
            "че",
            "умерла",
            "отстаньте"
        ])

# =====================================
# REPLY CHANCE
# =====================================

def should_reply(mentioned, reply_to_bot, active_chat):

    hour = datetime.now().hour

    if 2 <= hour <= 7:
        chance = 0.12
    else:
        chance = 0.42

    if mentioned:
        chance += 0.35

    if reply_to_bot:
        chance += 0.45

    if active_chat:
        chance += 0.15

    if current_mood == "грустная":
        chance -= 0.15

    return random.random() < chance

# =====================================
# MAIN
# =====================================

print("лиза онлайн 🖤")

while True:

    try:

        updates = get_updates(offset)

        for update in updates.get("result", []):

            offset = update["update_id"] + 1

            msg = update.get("message", {})

            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")
            message_id = msg.get("message_id")

            if not text or not chat_id:
                continue

            text_lower = text.lower()

            first_name = msg.get("from", {}).get("first_name", "")
            username = msg.get("from", {}).get("username", "")

            display_name = first_name if first_name else username

            # =====================================
            # ACTIVITY
            # =====================================

            if chat_id not in chat_activity:
                chat_activity[chat_id] = []

            chat_activity[chat_id].append(time.time())

            chat_activity[chat_id] = [
                t for t in chat_activity[chat_id]
                if time.time() - t < 120
            ]

            active_chat = len(chat_activity[chat_id]) >= 6

            # =====================================
            # REPLY DETECTION
            # =====================================

            reply_to_bot = False

            if msg.get("reply_to_message"):

                replied = msg["reply_to_message"]

                replied_user = replied.get("from", {}).get("username", "")

                if replied_user.lower() == BOT_USERNAME.lower():
                    reply_to_bot = True

            # =====================================
            # MENTION DETECTION
            # =====================================

            mentioned = (
                BOT_USERNAME.lower() in text_lower or
                any(word in text_lower for word in TRIGGER_WORDS)
            )

            # =====================================
            # SPONTANEOUS MESSAGE
            # =====================================

            spontaneous = False

            if active_chat and random.random() < 0.08:
                spontaneous = True

            # =====================================
            # SHOULD RESPOND
            # =====================================

            if not mentioned and not spontaneous and not reply_to_bot:
                continue

            if not should_reply(
                mentioned,
                reply_to_bot,
                active_chat
            ):
                continue

            # =====================================
            # RANDOM REACTIONS
            # =====================================

            if random.random() < 0.07:
                react(chat_id, message_id)

            # =====================================
            # MEMORY
            # =====================================

            remember_user(display_name, text)

            if chat_id not in chat_histories:
                chat_histories[chat_id] = []

            if chat_id not in last_replies:
                last_replies[chat_id] = []

            memory_text = ""

            for user, info in user_memory.items():

                memory_text += (
                    f"{user}: "
                    f"{info['relationship']}\n"
                )

            # =====================================
            # RECENT CHAT CONTEXT
            # =====================================

            recent_context = ""

            recent_messages = chat_histories[chat_id][-8:]

            for m in recent_messages:

                if m["role"] == "user":
                    recent_context += m["content"] + "\n"

            # =====================================
            # ADD MESSAGE
            # =====================================

            chat_histories[chat_id].append({

                "role": "user",

                "content": f"""
чат:
{recent_context}

память:
{memory_text}

{display_name}: {text}
"""
            })

            # =====================================
            # LIMIT MEMORY
            # =====================================

            if len(chat_histories[chat_id]) > 35:
                chat_histories[chat_id] = chat_histories[chat_id][-35:]

            # =====================================
            # RANDOM SELF MESSAGE
            # =====================================

            if random.random() < 0.01:

                random_msg = random.choice(
                    RANDOM_LIFE_MESSAGES
                )

                send_message(chat_id, random_msg)

            # =====================================
            # FAKE HUMAN
            # =====================================

            typing(chat_id)

            delay = random.uniform(1.2, 6.0)

            if random.random() < 0.15:
                delay += random.uniform(3, 10)

            time.sleep(delay)

            # иногда печатает и исчезает
            if random.random() < 0.03:
                continue

            # =====================================
            # GENERATE REPLY
            # =====================================

            reply = ask_groq(
                chat_histories[chat_id]
            )

            # =====================================
            # ANTI REPEAT
            # =====================================

            if reply in last_replies[chat_id]:
                continue

            last_replies[chat_id].append(reply)

            if len(last_replies[chat_id]) > 15:
                last_replies[chat_id] = (
                    last_replies[chat_id][-15:]
                )

            # =====================================
            # SAVE HISTORY
            # =====================================

            chat_histories[chat_id].append({
                "role": "assistant",
                "content": reply
            })

            # =====================================
            # SEND
            # =====================================

            send_message(
                chat_id,
                reply,
                reply_to=message_id if random.random() < 0.7 else None
            )

    except Exception as e:

        print("ошибка:", e)

        time.sleep(3)
```
