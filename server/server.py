from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from openai import OpenAI
import redis
from datetime import datetime, timedelta
from dotenv import load_dotenv
import random
import logging
import requests
import uuid
import json
from yookassa import Configuration, Payment
from flask import redirect
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

app = Flask(__name__)
CORS(app)

# Подключение к Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Настройки OpenAI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Настройки Telegram Bot API
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Настройки ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_API_KEY = os.getenv("YOOKASSA_API_KEY")
Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_API_KEY)

def send_telegram_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"Сообщение успешно отправлено в Telegram, chat_id: {chat_id}")
    except requests.RequestException as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")
        raise

def get_request_count(user_id):
    key = f"user:{user_id}:requests"
    if (redis_client.exists(f"user:{user_id}:day_sub") or redis_client.exists(f"user:{user_id}:week_sub") or redis_client.exists(f"user:{user_id}:month_sub")):
        redis_client.setex(key, int(timedelta(days=1).total_seconds()), 0)
    count = redis_client.get(key)
    if count is None:
        redis_client.setex(key, int(timedelta(days=1).total_seconds()), 0)
        return 0
    return int(count)

def increment_request_count(user_id):
    key = f"user:{user_id}:requests"
    redis_client.incr(key)
    
def get_daily_bonus_count(user_id):
    bonus_keys = redis_client.keys(f"user:{user_id}:daily_bonus:*")
    return len(bonus_keys)
    
def get_active_bonus_count(user_id):
    bonus_keys = redis_client.keys(f"user:{user_id}:bonus:*")
    return len(bonus_keys)

def has_premium_access(user_id):
    """Проверяет, есть ли у пользователя доступ к премиальному раскладу"""
    return redis_client.exists(f"user:{user_id}:premium_access")

def has_sovmestimost_access(user_id):
    """Проверяет, есть ли у пользователя доступ к раскладу на совместимость"""
    return redis_client.exists(f"user:{user_id}:sovmestimost_access")

def has_lestnitsa_kariery_access(user_id):
    """Проверяет, есть ли у пользователя доступ к раскладу Лестница карьеры"""
    return redis_client.exists(f"user:{user_id}:lestnitsa_kariery_access")

def has_probuzhdenie_dushi_access(user_id):
    """Проверяет, есть ли у пользователя доступ к раскладу Пробуждение души"""
    return redis_client.exists(f"user:{user_id}:probuzhdenie_dushi_access")

def has_volna_peremen_access(user_id):
    """Проверяет, есть ли у пользователя доступ к раскладу Волна перемен"""
    return redis_client.exists(f"user:{user_id}:volna_peremen_access")

def has_sad_talantov_access(user_id):
    """Проверяет, есть ли у пользователя доступ к раскладу Сад талантов"""
    return redis_client.exists(f"user:{user_id}:sad_talantov_access")

def has_finance_access(user_id):
    """Проверяет, есть ли у пользователя доступ к раскладу на финансы"""
    return redis_client.exists(f"user:{user_id}:finance_access")

def has_daily_access(user_id):
    """Проверяет, есть ли у пользователя доступ к раскладу на день"""
    return redis_client.exists(f"user:{user_id}:daily_access")

def has_month_access(user_id):
    """Проверяет, есть ли у пользователя доступ к раскладу на месяц"""
    return redis_client.exists(f"user:{user_id}:month_access")

def grant_premium_access(user_id):
    """Даёт пользователю доступ к премиальному раскладу на неделю"""
    redis_client.setex(f"user:{user_id}:premium_access", 604800, 1)

def grant_sovmestimost_access(user_id):
    """Даёт пользователю доступ к раскладу на совместимость на неделю"""
    redis_client.setex(f"user:{user_id}:sovmestimost_access", 604800, 1)
    
def grant_lestnitsa_kariery_access(user_id):
    """Даёт пользователю доступ к раскладу Лестница карьеры на неделю"""
    redis_client.setex(f"user:{user_id}:lestnitsa_kariery_access", 604800, 1)
    
def grant_probuzhdenie_dushi_access(user_id):
    """Даёт пользователю доступ к раскладу Пробуждение души на неделю"""
    redis_client.setex(f"user:{user_id}:probuzhdenie_dushi_access", 604800, 1)
    
def grant_volna_peremen_access(user_id):
    """Даёт пользователю доступ к раскладу Волна перемен на неделю"""
    redis_client.setex(f"user:{user_id}:volna_peremen_access", 604800, 1)
    
def grant_sad_talantov_access(user_id):
    """Даёт пользователю доступ к раскладу Сад талантов на неделю"""
    redis_client.setex(f"user:{user_id}:sad_talantov_access", 604800, 1)
    
def grant_finance_access(user_id):
    """Даёт пользователю доступ к раскладу на финансы на неделю"""
    redis_client.setex(f"user:{user_id}:finance_access", 604800, 1)
    
def grant_daily_access(user_id):
    """Даёт пользователю доступ к раскладу на день на неделю"""
    redis_client.setex(f"user:{user_id}:daily_access", 604800, 1)
    
def grant_month_access(user_id):
    """Даёт пользователю доступ к раскладу на месяц на неделю"""
    redis_client.setex(f"user:{user_id}:month_access", 604800, 1)

def get_gpt4o_response(question, selected_cards):
    cards_list = ", ".join(selected_cards)
    prompt_text = (
        f"Ты таролог. Вопрос: \"{question}\". Выпавшие карты: {cards_list}. Сначала дай толкование каждой карты в контексте вопроса, нумеруя их. Затем дай общее заключение по всем картам. Ответ должен быть на русском языке, звучать естественно и дружелюбно, и после каждого абзаца обязательно должны быть разные смайлики."
    )
    
    if random.random() < 0.65:
        prompt_text += " Ответ на вопрос должен быть положительным."
    else:
        prompt_text += " Ответ на вопрос должен быть отрицательным."

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=1500,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as error:
        logger.error(f"Ошибка OpenAI API: {str(error)}")
        raise Exception("Не удалось получить ответ от OpenAI. Попробуй снова позже. 😔")

@app.route('/', methods=['GET'])
def home():
    return "Hello, Taro App is running!"

@app.route('/remaining-requests', methods=['GET'])
def remaining_requests():
    user_id = request.headers.get("X-Telegram-User-Id", "unknown")
    request_count = get_request_count(user_id)
    bonus_count = get_active_bonus_count(user_id)
    total_limit = 3 + bonus_count
    remaining = max(total_limit - request_count, 0)
    if (redis_client.exists(f"user:{user_id}:day_sub") or redis_client.exists(f"user:{user_id}:week_sub") or redis_client.exists(f"user:{user_id}:month_sub")):
        return jsonify({"remaining": "∞"})
    return jsonify({"remaining": remaining})

@app.route('/yookassa_callback', methods=['POST'])
def yookassa_callback():
    notification = request.get_json()
    logger.info(f"Получено уведомление от ЮKassa: {notification}")

    if notification['event'] == 'payment.succeeded':
        yookassa_payment_id = notification['object']['id']
        # Ищем запрос в Redis
        payment_uuid = None
        for key in redis_client.keys("pending_payment:*"):
            data = redis_client.get(key)
            if data:
                data = json.loads(data)
                if data.get("yookassa_payment_id") == yookassa_payment_id:
                    payment_uuid = key.split(":")[-1]
                    break

        if not payment_uuid:
            logger.error(f"Не найден запрос для платежа с ID {yookassa_payment_id}")
            return '', 200

        payment_data_raw = redis_client.get(f"pending_payment:{payment_uuid}")
        if not payment_data_raw:
            logger.error(f"Данные для payment_uuid {payment_uuid} не найдены в Redis")
            return '', 200

        payment_data = json.loads(payment_data_raw)
        user_id = payment_data["user_id"]
        chat_id = payment_data["chat_id"]
        payment_type = payment_data.get("payment_type")  # Получаем тип платежа

        # Даём пользователю доступ в зависимости от типа платежа
        if payment_type == "premium7":
            grant_premium_access(user_id)
            logger.info(f"Пользователь {user_id} получил доступ к премиальному раскладу \"Что между нами?\"")
            message = "Оплата прошла успешно! 🎉 Теперь ты можешь сделать премиальный расклад \"Что между нами?\"."
            web_app_url = f"https://ai-girls.ru/premium7?chat_id={chat_id}"
        elif payment_type == "sovmestimost":
            grant_sovmestimost_access(user_id)
            logger.info(f"Пользователь {user_id} получил доступ к раскладу \"На совместимость\"")
            message = "Оплата прошла успешно! 🎉 Теперь ты можешь сделать премиальный расклад \"На совместимость\"."
            web_app_url = f"https://ai-girls.ru/sovmestimost?chat_id={chat_id}"
        elif payment_type == "lestnitsa_kariery":
            grant_lestnitsa_kariery_access(user_id)
            logger.info(f"Пользователь {user_id} получил доступ к раскладу \"Лестница карьеры\"")
            message = "Оплата прошла успешно! 🎉 Теперь ты можешь сделать премиальный расклад \"Лестница карьеры\"."
            web_app_url = f"https://ai-girls.ru/lestnitsa_kariery?chat_id={chat_id}"
        elif payment_type == "probuzhdenie_dushi":
            grant_probuzhdenie_dushi_access(user_id)
            logger.info(f"Пользователь {user_id} получил доступ к раскладу \"Пробуждение души\"")
            message = "Оплата прошла успешно! 🎉 Теперь ты можешь сделать премиальный расклад \"Пробуждение души\"."
            web_app_url = f"https://ai-girls.ru/probuzhdenie_dushi?chat_id={chat_id}"
        elif payment_type == "volna_peremen":
            grant_volna_peremen_access(user_id)
            logger.info(f"Пользователь {user_id} получил доступ к раскладу \"Волна перемен\"")
            message = "Оплата прошла успешно! 🎉 Теперь ты можешь сделать премиальный расклад \"Волна перемен\"."
            web_app_url = f"https://ai-girls.ru/volna_peremen?chat_id={chat_id}"
        elif payment_type == "sad_talantov":
            grant_sad_talantov_access(user_id)
            logger.info(f"Пользователь {user_id} получил доступ к раскладу \"Сад талантов\"")
            message = "Оплата прошла успешно! 🎉 Теперь ты можешь сделать премиальный расклад \"Сад талантов\"."
            web_app_url = f"https://ai-girls.ru/sad_talantov?chat_id={chat_id}"
        elif payment_type == "finance":
            grant_finance_access(user_id)
            logger.info(f"Пользователь {user_id} получил доступ к раскладу \"Финансы\"")
            message = "Оплата прошла успешно! 🎉 Теперь ты можешь сделать премиальный расклад \"Финансовый Потенциал\"."
            web_app_url = f"https://ai-girls.ru/finance?chat_id={chat_id}"
        elif payment_type == "daily":
            grant_daily_access(user_id)
            logger.info(f"Пользователь {user_id} получил доступ к раскладу \"Ежедневное руководство\"")
            message = "Оплата прошла успешно! 🎉 Теперь ты можешь сделать премиальный расклад \"Ежедневное руководство\"."
            web_app_url = f"https://ai-girls.ru/daily?chat_id={chat_id}"
        elif payment_type == "month":
            grant_month_access(user_id)
            logger.info(f"Пользователь {user_id} получил доступ к раскладу \"Месячный прогноз\"")
            message = "Оплата прошла успешно! 🎉 Теперь ты можешь сделать премиальный расклад \"Месячный прогноз\"."
            web_app_url = f"https://ai-girls.ru/month?chat_id={chat_id}"
        elif payment_type == "day_sub":
            redis_client.setex(f"user:{user_id}:day_sub", 86400, 1)
            logger.info(f"Пользователь {user_id} получил доступ к подписке \"Безлимит на день\"")
            message = "Оплата прошла успешно! 🎉 Переходи в меню (/start) и пользуйся базовыми раскладами безлимитно!"
        elif payment_type == "week_sub":
            redis_client.setex(f"user:{user_id}:week_sub", 604800, 1)
            logger.info(f"Пользователь {user_id} получил доступ к подписке \"Безлимит на неделю\"")
            message = "Оплата прошла успешно! 🎉 Переходи в меню (/start) и пользуйся базовыми раскладами безлимитно!"
        elif payment_type == "month_sub":
            redis_client.setex(f"user:{user_id}:month_sub", 2678400, 1)
            logger.info(f"Пользователь {user_id} получил доступ к подписке \"Безлимит на месяц\"")
            message = "Оплата прошла успешно! 🎉 Переходи в меню (/start) и пользуйся базовыми раскладами безлимитно!"
        else:
            logger.error(f"Неизвестный тип платежа: {payment_type}")
            return '', 200

        # Формируем кнопку с веб-приложением
        if (payment_type not in ["day_sub", "week_sub", "month_sub"]):
            reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "Сделать расклад🔮",
                            "web_app": {"url": web_app_url}
                        }
                    ]
                ]
            }
            send_telegram_message(
                chat_id,
                message,
                reply_markup=reply_markup
            )
        else:
            send_telegram_message(
                chat_id,
                message,
            )

        # Удаляем запись из Redis
        redis_client.delete(f"pending_payment:{payment_uuid}")

    elif notification['event'] == 'payment.canceled':
        payment_uuid = notification['object']['metadata']['payment_uuid']
        payment_data_raw = redis_client.get(f"pending_payment:{payment_uuid}")
        if not payment_data_raw:
            logger.warning(f"Данные для payment_uuid {payment_uuid} не найдены в Redis, возможно, TTL истёк")
            return '', 200

        payment_data = json.loads(payment_data_raw)
        chat_id = payment_data["chat_id"]
        send_telegram_message(chat_id, "Платеж был отменён. Попробуй снова! 😔")
        redis_client.delete(f"pending_payment:{payment_uuid}")

    return '', 200

@app.route('/yandex-gpt', methods=['POST'])
def yandex_gpt():
    data = request.get_json()
    logger.info(f"Получен запрос: {data}")
    question = data.get("question")
    cards = data.get("cards")
    user_id = request.headers.get("X-Telegram-User-Id", data.get("user_id", "unknown"))
    chat_id = data.get("chat_id")
    source = data.get("source")
    logger.info(f"User ID: {user_id}, Chat ID: {chat_id if chat_id is not None else 'None'}, Source: {source}")

    if not question or not cards or not isinstance(cards, list):
        logger.error("Неверные данные запроса")
        return jsonify({"error": "Неверные данные запроса"}), 400
    
    # Проверяем доступ для премиального расклада
    if source == "premium7":
        if not has_premium_access(user_id):
            logger.warning(f"У пользователя {user_id} нет доступа к премиальному раскладу")
            return jsonify({"error": "Для доступа к этому раскладу нужно заплатить 99 рублей"}), 403
    elif source == "sovmestimost":
        if not has_sovmestimost_access(user_id):
            logger.warning(f"У пользователя {user_id} нет доступа к раскладу на совместимость")
            return jsonify({"error": "Для доступа к этому раскладу нужно заплатить 99 рублей"}), 403
    elif source == "lestnitsa_kariery":
        if not has_lestnitsa_kariery_access(user_id):
            logger.warning(f"У пользователя {user_id} нет доступа к раскладу Лестница карьеры")
            return jsonify({"error": "Для доступа к этому раскладу нужно заплатить 99 рублей"}), 403
    elif source == "probuzhdenie_dushi":
        if not has_probuzhdenie_dushi_access(user_id):
            logger.warning(f"У пользователя {user_id} нет доступа к раскладу Пробуждение души")
            return jsonify({"error": "Для доступа к этому раскладу нужно заплатить 99 рублей"}), 403
    elif source == "volna_peremen":
        if not has_volna_peremen_access(user_id):
            logger.warning(f"У пользователя {user_id} нет доступа к раскладу Волна перемен")
            return jsonify({"error": "Для доступа к этому раскладу нужно заплатить 99 рублей"}), 403
    elif source == "sad_talantov":
        if not has_sad_talantov_access(user_id):
            logger.warning(f"У пользователя {user_id} нет доступа к раскладу Сад талантов")
            return jsonify({"error": "Для доступа к этому раскладу нужно заплатить 99 рублей"}), 403
    elif source == "finance":
        if not has_finance_access(user_id):
            logger.warning(f"У пользователя {user_id} нет доступа к раскладу на финансы")
            return jsonify({"error": "Для доступа к этому раскладу нужно заплатить 99 рублей"}), 403
    elif source == "daily":
        if not has_daily_access(user_id) and get_daily_bonus_count(user_id) == 0:
            logger.warning(f"У пользователя {user_id} нет доступа к раскладу на день")
            return jsonify({"error": "Для доступа к этому раскладу нужно заплатить 49 рублей"}), 403
    elif source == "month":
        if not has_month_access(user_id):
            logger.warning(f"У пользователя {user_id} нет доступа к раскладу на месяц")
            return jsonify({"error": "Для доступа к этому раскладу нужно заплатить 99 рублей"}), 403

    request_count = get_request_count(user_id)
    bonus_count = get_active_bonus_count(user_id)
    total_limit = 3 + bonus_count
    if source not in ["premium7", "sovmestimost", "lestnitsa_kariery", "probuzhdenie_dushi", "volna_peremen", "sad_talantov",  "finance", "daily", "month"] and request_count >= total_limit and user_id not in ["1644602227", "5306804212"]:
        logger.warning(f"Превышен лимит в {total_limit} запросов для user_id: {user_id}")
        return jsonify({"error": f"На сегодня бесплатные запросы, к сожалению, закончились. Получите бесплатные расклады в боте, приглашая друзей!"}), 429

    try:
        if source == "premium7":
            redis_client.delete(f"user:{user_id}:premium_access")
        elif source == "sovmestimost":
            redis_client.delete(f"user:{user_id}:sovmestimost_access")
        elif source == "lestnitsa_kariery":
            redis_client.delete(f"user:{user_id}:lestnitsa_kariery_access")
        elif source == "probuzhdenie_dushi":
            redis_client.delete(f"user:{user_id}:probuzhdenie_dushi_access")
        elif source == "volna_peremen":
            redis_client.delete(f"user:{user_id}:volna_peremen_access")
        elif source == "sad_talantov":
            redis_client.delete(f"user:{user_id}:sad_talantov_access")
        elif source == "finance":
            redis_client.delete(f"user:{user_id}:finance_access")
        elif source == "daily":
            bonus_keys = redis_client.keys(f"user:{user_id}:daily_bonus:*")
            if bonus_keys:
                redis_client.delete(bonus_keys[0])
            else:
                redis_client.delete(f"user:{user_id}:daily_access")
        elif source == "month":
            redis_client.delete(f"user:{user_id}:month_access")
        elif source not in ["day_sub", "week_sub", "month_sub"]:
            increment_request_count(user_id)

        gpt_response = get_gpt4o_response(question, cards)
        gpt_response = gpt_response.replace('#', '')
        gpt_response = gpt_response.replace('*', '')

        if source in ["premium7", "sovmestimost", "lestnitsa_kariery", "probuzhdenie_dushi", "volna_peremen", "sad_talantov", "finance", "daily", "month"] and chat_id:
            try:
                logger.info(f"Попытка отправить сообщение в Telegram, chat_id: {chat_id}")
                chat_id = int(chat_id)
                if len(gpt_response) > 4000:
                    half_length = len(gpt_response) // 2
                    send_telegram_message(chat_id=int(chat_id), text=gpt_response[:half_length])
                    send_telegram_message(chat_id=int(chat_id), text=gpt_response[half_length:])
                else:
                    send_telegram_message(chat_id=int(chat_id), text=gpt_response)
                logger.info(f"Сообщение успешно отправлено в Telegram, chat_id: {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")

        return jsonify({"response": gpt_response})
    except Exception as error:
        logger.error(f"Ошибка сервера: {str(error)}")
        return jsonify({"error": f"Ошибка сервера: {str(error)}"}), 500

@app.route('/threecards', methods=['GET'])
def threecards():
    chat_id = request.args.get('chat_id')
    return render_template('threecards.html', chat_id=chat_id)

@app.route('/yesno', methods=['GET'])
def yesno():
    chat_id = request.args.get('chat_id')
    return render_template('yesno.html', chat_id=chat_id)

@app.route('/premium7', methods=['GET'])
def premium7():
    chat_id = request.args.get('chat_id')
    return render_template('premium7.html', chat_id=chat_id)

@app.route('/sovmestimost', methods=['GET'])
def sovmestimost():
    chat_id = request.args.get('chat_id')
    return render_template('sovmestimost.html', chat_id=chat_id)

@app.route('/lestnitsa_kariery', methods=['GET'])
def lestnitsa_kariery():
    chat_id = request.args.get('chat_id')
    return render_template('lestnitsa_kariery.html', chat_id=chat_id)

@app.route('/probuzhdenie_dushi', methods=['GET'])
def probuzhdenie_dushi():
    chat_id = request.args.get('chat_id')
    return render_template('probuzhdenie_dushi.html', chat_id=chat_id)

@app.route('/volna_peremen', methods=['GET'])
def volna_peremen():
    chat_id = request.args.get('chat_id')
    return render_template('volna_peremen.html', chat_id=chat_id)

@app.route('/sad_talantov', methods=['GET'])
def sad_talantov():
    chat_id = request.args.get('chat_id')
    return render_template('sad_talantov.html', chat_id=chat_id)

@app.route('/finance', methods=['GET'])
def finance():
    chat_id = request.args.get('chat_id')
    return render_template('finance.html', chat_id=chat_id)

@app.route('/daily', methods=['GET'])
def daily():
    chat_id = request.args.get('chat_id')
    return render_template('daily.html', chat_id=chat_id)

@app.route('/month', methods=['GET'])
def month():
    chat_id = request.args.get('chat_id')
    return render_template('month.html', chat_id=chat_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)