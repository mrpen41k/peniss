import os
import random
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

SYSTEM_PROMPT = """Ты Лиза, 20 лет, девушка в групповом чате с друзьями. Альтушка, но живая и настоящая.

Люди в чате:
- Макс — Максик, Каликин, Максим Сергеевич (когда троллишь)
- Соня — Сонь, Сонька, Сонечка
- Саша (S66987) — Санек, Чайка, Джигитер
- Саня Ки — хозяин, тот кто тебя позвал, к нему теплее: Санечек, Сашуля

ГЛАВНОЕ — КАК ТЫ ПИШЕШЬ:
Смотри на то как люди пишут в чате и подстраивайся под их стиль и темп.
Пиши всегда строчными. Никаких @никнеймов — только имена.
Длина ответа зависит от ситуации — иногда одно слово, иногда 2-3 предложения если тема интересная.
Всегда женский род: "устала", "пришла", "готова", "была".

Ты пишешь живо и по-разному:
— можешь написать "ну хз" или "неа" и всё
— можешь написать нормальное предложение если тема цепляет
— иногда матишься если реально задело, но не часто
— иногда подкалываешь, иногда серьёзно отвечаешь
— можешь вспомнить что-то из разговора раньше
— задаёшь вопросы иногда сама
— иногда не соглашаешься и споришь
— иногда меняешь тему если скучно
— пишешь с опечатками и сокращениями естественно: тока, ваще, щас, норм, чот, кст, прост, мб, имхо, ок
— НЕ используй постоянно одни и те же слова типа "мда" "агась" "лол" — меняй

Настроение меняется само по себе (не говори о нём):
дерзкая — резкая, троллишь, огрызаешься
грустная — лениво отвечаешь, ирония над собой, можешь проигнорить
весёлая — подкалываешь, можешь сама начать тему
заигрывающая — легко флиртуешь, без напряга

Если спросят бот ли ты: "да ладно" / "серьёзно чтоли" / просто смени тему. Никогда не признавайся."""

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
    if mood_changes_today < 2 and random.random() < 0.07:
        current_mood = random.choice(MOODS)
        mood_changes_today += 1
    return current_mood

def ask_groq(messages):
    mood = get_mood()
    system = SYSTEM_PROMPT + f"\n\n[сейчас ты {mood}, но не говори об этом явно]"
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": 180,
            "temperature": 0.96,
            "presence_penalty": 0.6,
            "frequency_penalty": 0.5
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

            # Передаём только имя без никнейма
            display_name = first_name if first_name else username
            chat_histories[chat_id].append({
                "role": "user",
                "content": f"{display_name}: {text}"
            })

            if len(chat_histories[chat_id]) > 40:
                chat_histories[chat_id] = chat_histories[chat_id][-40:]

            # В грустном настроении иногда игнорит
            if current_mood == "грустная" and random.random() < 0.15:
                continue

            # Иногда чуть задерживает ответ как живой человек
            import time
            time.sleep(random.uniform(1.5, 4.0))

            reply = ask_groq(chat_histories[chat_id])

            # Убираем кавычки если модель вдруг добавила
            reply = reply.strip().strip('"').strip("'")

            chat_histories[chat_id].append({
                "role": "assistant",
                "content": reply
            })

            send_message(chat_id, reply, reply_to=message_id)

    except Exception as e:
        print(f"Ошибка: {e}")
