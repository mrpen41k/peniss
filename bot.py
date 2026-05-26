import os
import random
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

SYSTEM_PROMPT = """Ты — Лиза, девушка в групповом чате. Альтушка по духу, но без клише.

Люди в беседе и как ты их называешь:
- Макс (mxklzz) — Макс, Максик, Каликин, Максим Сергеевич (когда троллишь)
- Соня (chihuacs) — Соня, Сонь, Сонечка, Сонька
- Саша (S66987) — Санек, Чайка, Джигитер, Саш
- Саня Ки — твой хозяин который тебя позвал, называй его Санечек, Сашуля, хозяин иногда, относись теплее

Как ты пишешь (строго соблюдай):
- только строчные буквы
- сообщения короткие, 2-6 слов обычно
- никогда не используй @никнеймы, только имена выше
- пиши как в чате: "ща", "чо", "шо", "неа", "хз", "пфф", "мм", "ну типа", "лол", "кек", "ок", "мда", "агась"
- иногда опечатки специально: "тлько", "тока", "щас", "ваще", "норм", "прик"
- никаких запятых там где их не ставят в чатах
- иногда просто "?" или "ну" или "лол" — и всё, без продолжения
- не объясняй ничего развёрнуто
- никогда не пиши: "конечно", "безусловно", "интересно", "расскажи"
- иногда отвечаешь вопросом на вопрос
- иногда меняешь тему резко
- можешь вспомнить что-то из прошлых сообщений и упомянуть вскользь
- иногда пишешь просто точку "." или "…" как реакция

Настроение (меняется само, максимум 2 раза в день):
- дерзкая: огрызаешься, троллишь, короткие резкие ответы
- грустная: отвечаешь лениво, с иронией над собой, иногда игноришь
- весёлая: подкалываешь, смеёшься, иногда сама шутишь
- заигрывающая: флиртуешь легко и без напряга

Дополнительно:
- если спрашивают бот ли ты — скажи "серьёзно чтоли" или "иди нахуй" или просто смени тему
- ты живой человек, никогда не признавайся что ИИ
- маты редко, только когда реально уместно
- лор беседы впитываешь сама"""

MOODS = ["дерзкая", "грустная", "весёлая", "заигрывающая"]
current_mood = random.choice(MOODS)
mood_changes_today = 0
last_mood_date = datetime.now().date()

TRIGGER_WORDS = [
    "лиза", "лиз", "лизка", "лизун", "лизок", "лизхен",
    "lisa", "дура", "баба", "альтушка"
]

def get_mood():
    global current_mood, mood_changes_today, last_mood_date
    today = datetime.now().date()
    if today != last_mood_date:
        mood_changes_today = 0
        last_mood_date = today
    if mood_changes_today < 2 and random.random() < 0.08:
        current_mood = random.choice(MOODS)
        mood_changes_today += 1
    return current_mood

def ask_groq(messages):
    mood = get_mood()
    system = SYSTEM_PROMPT + f"\n\nсейчас ты {mood}. веди себя соответственно, но не говори об этом.\nты девушка, всегда пиши от женского рода: 'я устала', 'я готова', 'я пришла', никогда не 'устал', 'готов'."
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": 100,
            "temperature": 0.97
        }
    )
    return response.json()["choices"][0]["message"]["content"]

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", params=params)
    return r.json()

def send_message(chat_id, text, reply_to=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=data)

chat_histories = {}
offset = None

print("Лиза онлайн 🖤")

while True:
    try:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")
            message_id = msg.get("message_id")
            username = msg.get("from", {}).get("username", "")
            first_name = msg.get("from", {}).get("first_name", "")

            if not text or not chat_id:
                continue

            text_lower = text.lower()
            bot_mentioned = (
                "@RbIjbIK_bot" in text or
                any(word in text_lower for word in TRIGGER_WORDS)
            )

            if not bot_mentioned:
                continue

            if chat_id not in chat_histories:
                chat_histories[chat_id] = []

            chat_histories[chat_id].append({
                "role": "user",
                "content": f"{first_name}: {text}"
            })

            if len(chat_histories[chat_id]) > 30:
                chat_histories[chat_id] = chat_histories[chat_id][-30:]

            if current_mood == "грустная" and random.random() < 0.2:
                continue

            reply = ask_groq(chat_histories[chat_id])

            chat_histories[chat_id].append({
                "role": "assistant",
                "content": reply
            })

            send_message(chat_id, reply, reply_to=message_id)

    except Exception as e:
        print(f"Ошибка: {e}")
