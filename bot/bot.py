from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import os
import redis
import logging
import asyncio
from datetime import datetime, timezone
import requests
import uuid
import json
import re
from yookassa import Configuration, Payment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

APP_LINK = "t.me/TaroBestFreebot/Taro777"

YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_API_KEY = os.getenv("YOOKASSA_API_KEY")
Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_API_KEY)

try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()  # Проверяем подключение
    logger.info("Успешно подключились к Redis")
except redis.ConnectionError as e:
    logger.error(f"Не удалось подключиться к Redis: {e}")
    raise

# Обработчик команды /referral
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"Твоя реферальная ссылка: {referral_link}\n"
        "Поделись ей с друзьями, и за каждого нового пользователя ты получишь доступ к премиальному раскладу \"Ежедневное руководство\"! 🚀"
    )

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    chat_id = update.effective_chat.id
    logger.info(f"Chat ID в bot.py: {chat_id}")

    # Проверяем, есть ли реферальный параметр
    if context.args:
        try:
            referrer_id = int(context.args[0])
            # Убеждаемся, что пользователь не сам себе реферер и ещё не зарегистрирован
            if referrer_id != user_id and not redis_client.sismember("bot_users", user_id):
                # Записываем реферала
                redis_client.sadd(f"referrals:{referrer_id}", user_id)
                # Начисляем бонус рефереру на 24 часа
                unique_id = datetime.now(timezone.utc).isoformat()
                bonus_key = f"user:{referrer_id}:daily_bonus:{unique_id}"
                redis_client.setex(bonus_key, 604800, 1)
                logger.info(f"Пользователь {user_id} пришёл по приглашению {referrer_id}")
                try:
                    await context.bot.send_message(
                        referrer_id,
                        "Кто-то присоединился по твоей ссылке!💫\nТы получил доступ к премиальному раскладу \"Ежедневное руководство\"!\n\nНажимай /start, переходи в раздел премиальных раскладов, выбирай расклад \"Ежедневное руководство\" и узнай, что ждет тебя в течение дня 🚀",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление рефереру {referrer_id}: {e}")
        except ValueError:
            logger.error(f"Некорректный параметр реферала: {context.args[0]}")

    # Регистрируем пользователя, если он ещё не зарегистрирован
    if not redis_client.sismember("bot_users", user_id):
        redis_client.sadd("bot_users", user_id)
        redis_client.hset(f"user:{user_id}", "username", username)

    keyboard = [
        [InlineKeyboardButton(text="Бесплатные расклады✨", callback_data="free")],
        [InlineKeyboardButton(text="Премиальные расклады💞", callback_data="menu")],
        [InlineKeyboardButton(text="Купить подписку💰", callback_data="sub")],
        [InlineKeyboardButton(text="Бесплатный премиум🚀", callback_data="referral")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text=(
            "*Добро пожаловать в мир Таро!* 🎴\n\n"
            "Карты готовы рассказать о твоём будущем, любви и скрытых возможностях.\n"
            "Выбери расклад и узнай, что ждёт тебя впереди ✨"
        ),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Обработчик для callback-запросов
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    user_id = query.from_user.id
    callback_data = query.data
    
    # Сбрасываем ожидание email при любом действии с кнопками
    if context.user_data.get('awaiting_email'):
        context.user_data['awaiting_email'] = False

    if callback_data == "premium7_info":
        info_message = (
            "*Расклад \"Что между нами?\"* 💖\n\n"
            "Хочешь заглянуть в сердце того, кто тебе так важен? "
            "Этот расклад из 7 карт раскроет все тайны ваших отношений. 🌸\n\n"
            "Вот что ты узнаешь:\n"
            "*1. Как он(а) тебя видит?* — Что он(а) думает о тебе, когда смотрит на тебя?\n"
            "*2. Как он(а) тебя чувствует?* — Какие эмоции ты вызываешь в его(её) сердце?\n"
            "*3. Как он(а) ведёт себя на самом деле?* — Что скрывается за его(её) поступками?\n"
            "*4. Как он(а) воспринимает ваши отношения?* — Что для него(неё) значат ваши связи?\n"
            "*5. Чего он(а) хочет от тебя?* — Его(её) истинные желания и ожидания.\n"
            "*6. Что мешает вашим отношениям?* — Какие преграды стоят на вашем пути?\n"
            "*7. Возможное будущее.* — Куда приведёт вас эта дорога?\n\n"
            "Стоимость расклада: *99 рублей*.\n"
            "*Расклад так же дублируется в этот чат.*\n"
        )
        # Проверяем, есть ли доступ к премиальному раскладу
        has_access = redis_client.exists(f"user:{user_id}:premium_access")
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Сделать расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru/premium7?chat_id={chat_id}"))],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\n\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n*Пожалуйста, введите свой email:*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "premium7"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email

    elif callback_data == "sovmestimost_info":
        info_message = (
            "*Расклад \"Совместимость\"* 💞\n\n"
            "Хочешь узнать, насколько вы подходите друг другу? "
            "Этот расклад из 8 карт поможет понять, что вас объединяет, а что может стать вызовом. 🌟\n\n"
            "Вот что ты узнаешь:\n"
            "*1. Сущность первого человека* - Описание ключевых качеств, жизненных установок и эмоционального состояния первого партнёра.\n"
            "*2. Сущность второго человека* - Аналогичное описание для второго партнёра — его индивидуальные особенности и ценности.\n"
            "*3. Энергетическое соединение* - Показывает, как сходятся и взаимодействуют энергетики обоих людей, насколько их потоки синхронизированы.\n"
            "*4. Эмоциональное взаимопонимание* - Определяет, насколько близко они ощущают и понимают эмоциональные состояния друг друга, как выражаются чувства.\n"
            "*5. Интеллектуальная и коммуникативная связь* - Раскрывает уровень взаимопонимания в общении, сходство взглядов и способность делиться мыслями.\n"
            "*6. Физическая и сексуальная химия* - Указывает на степень физического притяжения и сексуальную гармонию между партнёрами.\n"
            "*7. Потенциальные препятствия и вызовы* - Обозначает возможные трудности, внутренние или внешние факторы, которые могут влиять на развитие отношений.\n"
            "*8. Общее будущее и совместное развитие* - Показывает потенциал развития отношений, возможное направление общего пути и даёт совет по дальнейшим действиям.\n\n"
            "Стоимость расклада: *99 рублей*.\n"
            "*Расклад так же дублируется в этот чат.*\n"
        )
        has_access = redis_client.exists(f"user:{user_id}:sovmestimost_access")
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Сделать расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru/sovmestimost?chat_id={chat_id}"))],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\n\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n*Пожалуйста, введите свой email:*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "sovmestimost"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "sad_talantov_info":
        info_message = (
            "<b>Расклад \"Сад талантов\"</b> 🌸\n\n"
            "Хочешь раскрыть свои уникальные способности и найти путь к самореализации?\n"
            "Этот глубокий расклад из 9 карт поможет понять, какие таланты в тебе скрыты, что мешает их проявлению и как расцвести в полной мере! 🌟\n\n"
            "Вот что ты узнаешь:\n"
            "<b>1. Ядро личности</b> - Кто ты в глубине души, какой главный дар лежит в основе твоего потенциала?\n"
            "<b>2. Прошлый опыт</b> - Как твои таланты проявлялись раньше и что они тебе дали?\n"
            "<b>3. Текущая возможность</b> - Где и как ты можешь применить свои способности прямо сейчас?\n"
            "<b>4. Внутренний барьер</b> - Какие страхи или убеждения сдерживают твою самореализацию?\n"
            "<b>5. Внешний барьер</b> - Какие внешние обстоятельства мешают раскрытию твоих талантов?\n"
            "<b>6. Ключевое действие</b> - Какой шаг нужно сделать, чтобы начать проявлять свои способности?\n"
            "<b>7. Поддержка окружения</b> - Кто или что поможет тебе сиять ярче?\n"
            "<b>8. Краткосрочный результат</b> - Что принесёт использование твоих талантов в ближайшем будущем?\n"
            "<b>9. Долгосрочное видение</b> - Куда приведёт развитие твоих талантов в перспективе?\n\n"
            "Стоимость расклада: <b><s>149</s> 99 рублей</b>.\n"
            "<b>Расклад так же дублируется в этот чат.</b>\n"
        )
        bonus_keys = redis_client.keys(f"user:{user_id}:sad_talantov_bonus:*")
        has_access = redis_client.exists(f"user:{user_id}:sad_talantov_access") or len(bonus_keys) > 0
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Сделать расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru/sad_talantov?chat_id={chat_id}"))],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\n\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "sad_talantov"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "volna_peremen_info":
        info_message = (
            "<b>Расклад \"Волна перемен\"</b> 🌊\n\n"
            "Готов встретить перемены с уверенностью?\n"
            "Этот глубокий расклад из 8 карт поможет разобраться, что происходит в твоей жизни, как адаптироваться к изменениям и какие возможности они несут! 🌟\n\n"
            "Вот что ты узнаешь:\n"
            "<b>1. Текущая ситуация</b> - Что происходит в твоей жизни прямо сейчас?\n"
            "<b>2. Причина перемен</b> - Что вызвало эти изменения и почему они пришли?\n"
            "<b>3. Страх или сопротивление</b> - Что мешает тебе принять перемены?\n"
            "<b>4. Скрытая возможность</b> - Какой потенциал таят в себе эти изменения?\n"
            "<b>5. Необходимое действие</b> - Какой шаг поможет адаптироваться к переменам?\n"
            "<b>6. Поддержка окружения</b> - Кто или что поможет тебе в этом переходе?\n"
            "<b>7. Краткосрочный исход</b> - Что произойдёт в ближайшем будущем?\n"
            "<b>8. Долгосрочный результат</b> - Куда приведут эти перемены в перспективе?\n\n"
            "Стоимость расклада: <b><s>149</s> 99 рублей</b>.\n"
            "<b>Расклад так же дублируется в этот чат.</b>\n"
        )
        bonus_keys = redis_client.keys(f"user:{user_id}:volna_peremen_bonus:*")
        has_access = redis_client.exists(f"user:{user_id}:volna_peremen_access") or len(bonus_keys) > 0
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Сделать расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru/volna_peremen?chat_id={chat_id}"))],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\n\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "volna_peremen"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "probuzhdenie_dushi_info":
        info_message = (
            "<b>Расклад \"Пробуждение души\"</b> ✨\n\n"
            "Хочешь найти свой истинный путь и раскрыть духовный потенциал?\n"
            "Этот глубокий расклад из 9 карт поможет понять, где ты находишься на духовном пути, какие уроки ждут и как соединиться с высшим Я! 🌟\n\n"
            "Вот что ты узнаешь:\n"
            "<b>1. Душа сейчас</b> - Каково твоё текущее духовное состояние?\n"
            "<b>2. Прошлый духовный опыт</b> - Что сформировало твой духовный путь?\n"
            "<b>3. Скрытый дар</b> - Какой духовный талант или интуиция в тебе скрыты?\n"
            "<b>4. Текущий урок</b> - Какой урок Вселенная преподаёт тебе сейчас?\n"
            "<b>5. Препятствие на пути</b> - Что блокирует твой духовный рост?\n"
            "<b>6. Необходимое действие</b> - Какой шаг приблизит тебя к пробуждению?\n"
            "<b>7. Внешняя поддержка</b> - Кто или что помогает на твоём пути?\n"
            "<b>8. Будущий потенциал</b> - К чему приведёт твой духовный рост?\n"
            "<b>9. Послание высших сил</b> - Финальный совет от карт для твоей души.\n\n"
            "Стоимость расклада: <b><s>149</s> 99 рублей</b>.\n"
            "<b>Расклад так же дублируется в этот чат.</b>\n"
        )
        bonus_keys = redis_client.keys(f"user:{user_id}:probuzhdenie_dushi_bonus:*")
        has_access = redis_client.exists(f"user:{user_id}:probuzhdenie_dushi_access") or len(bonus_keys) > 0
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Сделать расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru/probuzhdenie_dushi?chat_id={chat_id}"))],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\n\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "probuzhdenie_dushi"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "lestnitsa_kariery_info":
        info_message = (
            "<b>Расклад \"Лестница карьеры\"</b> 🚀\n\n"
            "Мечтаешь о карьерном прорыве или новом этапе в работе?\n"
            "Этот глубокий расклад из 9 карт покажет, где ты находишься в профессиональном плане, что мешает успеху и как достичь вершины! 🌟\n\n"
            "Вот что ты узнаешь:\n"
            "<b>1. Прошлое в карьере</b> - Что сформировало твою текущую профессиональную ситуацию?\n"
            "<b>2. Текущая позиция</b> - Где ты находишься в своей карьере прямо сейчас?\n"
            "<b>3. Скрытый потенциал</b> - Какие неиспользованные возможности или таланты у тебя есть?\n"
            "<b>4. Препятствие на пути</b> - Что мешает твоему карьерному росту?\n"
            "<b>5. Ключевая возможность</b> - Какой шанс стоит использовать для продвижения?\n"
            "<b>6. Необходимое действие</b> - Какой шаг нужно сделать прямо сейчас?\n"
            "<b>7. Поддержка окружения</b> - Кто или что поможет в твоей карьере?\n"
            "<b>8. Краткосрочный результат</b> - Что произойдёт в ближайшие месяцы?\n"
            "<b>9. Долгосрочная перспектива</b> - Куда приведёт твой текущий карьерный путь?\n\n"
            "Стоимость расклада: <b><s>149</s> 99 рублей</b>.\n"
            "<b>Расклад так же дублируется в этот чат.</b>\n"
        )
        bonus_keys = redis_client.keys(f"user:{user_id}:lestnitsa_kariery_bonus:*")
        has_access = redis_client.exists(f"user:{user_id}:lestnitsa_kariery_access") or len(bonus_keys) > 0
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Сделать расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru/lestnitsa_kariery?chat_id={chat_id}"))],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\n\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "lestnitsa_kariery"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "finance_info":
        info_message = (
            "<b>Расклад \"Финансовый Потенциал\"</b> 💵\n\n"
            "Хочешь раскрыть свои денежные возможности?\n"
            "Этот детальный расклад из 7 карт покажет, где ты сейчас в финансовом плане, что тебе мешает разбогатеть и где скрыты твои денежные ресурсы. 🌟\n\n"
            "Вот что ты узнаешь:\n"
            "<b>1. Текущее финансовое положение</b> - что происходит сейчас в финансовой сфере, каковы основные тенденции и энергия.\n"
            "<b>2. Главное препятствие</b> - то, что мешает улучшить финансы: внешние обстоятельства, внутренние установки, поведение.\n"
            "<b>3. Источник дохода</b> - где лежит главный или потенциальный источник денег, на что стоит опереться.\n"
            "<b>4. Скрытые ресурсы</b> - способности, связи, таланты или ситуации, которые можно использовать, но они пока не осознаны.\n"
            "<b>5. Финансовое будущее (ближайшее)</b> - как будут развиваться события в ближайшем времени, если всё пойдёт по текущему сценарию.\n"
            "<b>6. Финансовое будущее (долгосрочное)</b> - общая перспектива развития финансов в более отдалённой перспективе.\n"
            "<b>7. Совет Таро</b> - что стоит делать, чтобы улучшить свою финансовую ситуацию, в каком направлении двигаться.\n\n"
            "Стоимость расклада: <b>99 рублей</b>.\n"
            "<b>Расклад так же дублируется в этот чат.</b>\n"
        )
        has_access = redis_client.exists(f"user:{user_id}:finance_access")
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Сделать расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru/finance?chat_id={chat_id}"))],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\n\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "finance"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "daily_info":
        info_message = (
            "<b>Расклад \"Ежедневное руководство\"</b> 💵\n\n"
            "Каждый новый день открывает перед вами бесконечные возможности, и этот расклад поможет найти точку опоры, определить приоритеты и избежать неожиданных ловушек! 💫\n"
            "Вот что ты узнаешь:\n"
            "<b>1. Утренний настрой</b> — с каким энергетическим фоном ты входишь в день, что влияет на твоё самочувствие и внутреннее состояние с самого утра.\n"
            "<b>2. Главная задача</b> — на чём стоит сосредоточить внимание сегодня, в какой сфере будет важно проявиться.\n"
            "<b>3. Предупреждение</b> — возможные ловушки, ошибки или события, которые могут сбить с пути или усложнить день.\n"
            "<b>4. Ресурс дня</b> — твоя поддержка: внутренние качества, внешние обстоятельства или люди, которые помогут справиться с задачами.\n"
            "<b>5. Неожиданность</b> — что может внезапно появиться в течение дня и потребует твоего внимания или реакции.\n"
            "<b>6. Вечерний урок</b> — чему научит этот день, какой опыт ты получишь к его завершению.\n"
            "<b>7. Вывод дня</b> — итоговое послание Таро: с чем ты завершишь день и что важно взять с собой в завтрашний.\n\n"
            "Стоимость расклада: <b><s>99</s> 49 рублей</b>.\n"
            "<b>Расклад так же дублируется в этот чат.</b>\n"
        )
        bonus_keys = redis_client.keys(f"user:{user_id}:daily_bonus:*")
        has_access = redis_client.exists(f"user:{user_id}:daily_access") or len(bonus_keys) > 0
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Сделать расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru/daily?chat_id={chat_id}"))],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\n\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "daily"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "month_info":
        info_message = (
            "<b>Расклад \"Месячный прогноз\"</b> 🌙\n\n"
            "Хочешь узнать, что готовит тебе ближайший месяц? Этот расклад откроет основные события, настроения и скрытые возможности. Карты подскажут, на что обратить внимание и как прожить месяц максимально осознанно! 💫\n\n"
            "Вот что ты узнаешь:\n"
            "<b>1. Общая энергия месяца</b> — какое настроение и атмосфера будут сопровождать тебя в течение месяца, какой будет общий эмоциональный и событийный фон.\n"
            "<b>2. Главное событие месяца</b> — ключевое событие или поворотный момент, который окажет наибольшее влияние на твою жизнь.\n"
            "<b>3. Финансы и работа</b> — что ждёт в профессиональной сфере: возможности, риски и потенциал роста.\n"
            "<b>4. Личная жизнь и отношения</b> — как будут развиваться романтические и/или семейные отношения, новые знакомства или внутренние перемены.\n"
            "<b>5. Здоровье и энергия</b> — на что обратить внимание в физическом и эмоциональном состоянии, как поддерживать ресурсность.\n"
            "<b>6. Возможности и дары месяца</b> — неожиданные шансы, удачные стечения обстоятельств, скрытые плюсы периода.\n"
            "<b>7. Совет Таро</b> — как лучше всего прожить этот месяц: что усилить, что отпустить, на что направить фокус.\n\n"
            "Стоимость расклада: <b><s>199</s> 99 рублей</b>.\n"
            "<b>Расклад так же дублируется в этот чат.</b>\n"
        )
        has_access = redis_client.exists(f"user:{user_id}:month_access")
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Сделать расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru/month?chat_id={chat_id}"))],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\n\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "month"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "referral":
        user_id = update.effective_user.id
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        info_message = (
            f"Твоя реферальная ссылка: {referral_link}\n"
            "Поделись ей с друзьями, и за каждого нового пользователя ты получишь доступ к премиальному раскладу \"Ежедневное руководство\"! 🚀"
        )
        # Кнопка для перехода в WebApp
        keyboard = [
            [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            text=info_message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif callback_data == "menu":
        keyboard = [
            [InlineKeyboardButton(text="\"Сад талантов\"🌸", callback_data="sad_talantov_info")],
            [InlineKeyboardButton(text="\"Волна перемен\"🌊", callback_data="volna_peremen_info")],
            [InlineKeyboardButton(text="\"Пробуждение души\"✨", callback_data="probuzhdenie_dushi_info")],
            [InlineKeyboardButton(text="\"Лестница карьеры\"🚀", callback_data="lestnitsa_kariery_info")],
            [InlineKeyboardButton(text="\"Ежедневное руководство\"💫", callback_data="daily_info")],
            [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            text=(
                "*Добро пожаловать в мир премиальных раскладов!* 🌟\n\n"
                "*Почему премиум?*\n"
                "*1. Ответ навсегда сохраняется в чате* — ты всегда сможешь перечитать его, даже через месяцы! ⏳\n"
                "*2. Минимум 7 карт* — это не просто ответ «да/нет». Каждая позиция раскрывает новый слой ситуации: причины, скрытые влияния, варианты решений, прогноз. ✨\n"
                "*3. Подробное описание* — наиболее глубокий анализ и подробный вывод из ситуации. 📜\n\n"
                "Скорее выбирай расклад и погрузись в мир, где каждая деталь имеет значение! 💞"
            ),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif callback_data == "free":
        keyboard = [
            [InlineKeyboardButton(text="Расклад на любовь💘", web_app=WebAppInfo(url=f"https://ai-girls.ru/threecards?chat_id={chat_id}"))],
            [InlineKeyboardButton(text="Общий расклад🔮", web_app=WebAppInfo(url=f"https://ai-girls.ru?chat_id={chat_id}"))],
            [InlineKeyboardButton(text="Расклад Да/Нет👀", web_app=WebAppInfo(url=f"https://ai-girls.ru/yesno?chat_id={chat_id}"))],
            [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            text=(
                "*Добро пожаловать в мир бесплатных раскладов!* 🌟\n\n"
                "*Почему стоит попробовать?*\n"
                "*1. Быстрый и понятный ответ* — идеально, если нужны подсказки здесь и сейчас. ⚡\n"
                "*2. Компактный формат* — лаконичное описание без лишней воды, но с ключевыми выводами. 📌\n"
                "*3. Доступность* — возможность получить совет без ожидания и сложностей. 💫\n\n"
                "Выбирай расклад и исследуй ситуацию легко и с удовольствием! 🌈"
            ),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif callback_data == "sub":
        keyboard = [
            [InlineKeyboardButton(text="Безлимит на день", callback_data="day_sub")],
            [InlineKeyboardButton(text="Безлимит на неделю", callback_data="week_sub")],
            [InlineKeyboardButton(text="Безлимит на месяц", callback_data="month_sub")],
            [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            text=(
                "*Добро пожаловать в мир подписок!* 🌟\n\n"
                "С подпиской ты получаешь *безлимитный* доступ к базовым раскладам Таро на выбранный период:\n"
                "*1. Общий расклад* — ответ на любой интересующий вопрос.\n"
                "*2. Расклад на любовь* — расклад на вопрос об отношениях и чувствах.\n"
                "*3. Расклад \"Да/Нет\"* — четкий ответ на любой вопрос.\n\n"
                "Выбирай свой формат и позволь картам раскрыть твое будущее! ✨"
            ),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif callback_data == "day_sub":
        info_message = (
            "<b>Подписка \"Безлимит на день\"</b> 🌟\n\n"
            "Стоимость подписки: <b>49 рублей</b>.\n"
        )
        has_access = redis_client.exists(f"user:{user_id}:day_sub")
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message + "\n<b>У Вас уже активирована подписка.</b> Нажимай /start и делай безлимитные базовые расклады!",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "day_sub"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "week_sub":
        info_message = (
            "<b>Подписка \"Безлимит на неделю\"</b> 🌟\n\n"
            "Стоимость подписки: <b>99 рублей</b>.\n"
        )
        has_access = redis_client.exists(f"user:{user_id}:week_sub")
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message + "\n<b>У Вас уже активирована подписка.</b> Нажимай /start и делай безлимитные базовые расклады!",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "week_sub"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "month_sub":
        info_message = (
            "<b>Подписка \"Безлимит на месяц\"</b> 🌟\n\n"
            "Стоимость подписки: <b>299 рублей</b>.\n"
        )
        has_access = redis_client.exists(f"user:{user_id}:month_sub")
        if has_access:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=info_message + "\n<b>У Вас уже активирована подписка.</b> Нажимай /start и делай безлимитные базовые расклады!",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Запрашиваем email перед оплатой
            await query.message.reply_text(
                text=info_message + "\nДля оплаты мне нужен ваш email, чтобы отправить чек. 📜\n<b>Пожалуйста, введите свой email:</b>",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data['chat_id'] = chat_id
            context.user_data['user_id'] = user_id
            context.user_data['awaiting_email'] = True  # Устанавливаем флаг ожидания email
            context.user_data['payment_type'] = "month_sub"  # Указываем тип платежа
            return  # Прерываем выполнение, ждём ввода email
    elif callback_data == "back_to_start":
        # Удаляем предыдущее сообщение
        await query.message.delete()

# Обработчик ввода email
async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, ожидает ли бот email
    if not context.user_data.get('awaiting_email'):
        return  # Если не ждём email, игнорируем сообщение

    user_id = context.user_data['user_id']
    chat_id = context.user_data['chat_id']
    payment_type = context.user_data.get('payment_type')  # Получаем тип платежа
    
    if not (user_id and chat_id and payment_type):  # Проверяем, что данные актуальны
        context.user_data['awaiting_email'] = False
        return
    
    email = update.message.text.strip()

    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_pattern, email):
        logger.warning(f"Некорректный email в payment_data: {email}, используется заглушка")
        email = "user@example.com"

    redis_client.setex(f"user:{user_id}:email", 86400, email)
    logger.info(f"Email пользователя {user_id} сохранён: {email}")

    # Очищаем флаг ожидания email
    context.user_data['awaiting_email'] = False

    # Генерируем уникальный ID для платежа
    payment_uuid = str(uuid.uuid4())
    payment_data = {
        "user_id": str(user_id),
        "chat_id": str(chat_id),
        "email": email,
        "payment_type": payment_type  # Сохраняем тип платежа
    }

    try:
        # Определяем параметры платежа в зависимости от типа
        if payment_type == "premium7":
            amount = "99.00"
            description = "Премиальный расклад \"Что между нами?\""
        elif payment_type == "sovmestimost":
            amount = "99.00"
            description = "Премиальный расклад \"Совместимость\""
        elif payment_type == "sad_talantov":
            amount = "99.00"
            description = "Премиальный расклад \"Сад талантов\""
        elif payment_type == "volna_peremen":
            amount = "99.00"
            description = "Премиальный расклад \"Волна перемен\""
        elif payment_type == "probuzhdenie_dushi":
            amount = "99.00"
            description = "Премиальный расклад \"Пробуждение души\""
        elif payment_type == "lestnitsa_kariery":
            amount = "99.00"
            description = "Премиальный расклад \"Лестница карьеры\""
        elif payment_type == "finance":
            amount = "99.00"
            description = "Премиальный расклад \"Финансовый Потенциал\""
        elif payment_type == "daily":
            amount = "49.00"
            description = "Премиальный расклад \"Ежедневное руководство\""
        elif payment_type == "month":
            amount = "99.00"
            description = "Премиальный расклад \"Месячный прогноз\""
        elif payment_type == "day_sub":
            amount = "49.00"
            description = "Подписка \"Безлимит на день\""
        elif payment_type == "week_sub":
            amount = "99.00"
            description = "Подписка \"Безлимит на неделю\""
        elif payment_type == "month_sub":
            amount = "299.00"
            description = "Подписка \"Безлимит на месяц\""
        else:
            raise ValueError("Неизвестный тип платежа")

        # Создаём платёж в ЮKassa
        payment = Payment.create({
            "amount": {
                "value": amount,
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/TaroBestFreebot"
            },
            "capture": True,
            "description": description,
            "metadata": {"payment_uuid": payment_uuid},
            "receipt": {
                "customer": {
                    "email": email
                },
                "items": [
                    {
                        "description": description,
                        "quantity": 1,
                        "amount": {
                            "value": amount,
                            "currency": "RUB"
                        },
                        "vat_code": 1
                    }
                ]
            }
        })

        payment_data["yookassa_payment_id"] = payment.id
        redis_client.setex(f"pending_payment:{payment_uuid}", 3600, json.dumps(payment_data))
        payment_url = payment.confirmation.confirmation_url
        logger.info(f"Сгенерирована ссылка на оплату: {payment_url}")

        # Отправляем пользователю ссылку на оплату
        if (payment_type in ["day_sub", "week_sub", "month_sub"]):
            keyboard = [
                [InlineKeyboardButton(text=f"Купить подписку🔮 - {amount}₽", url=payment_url)],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                text="Спасибо! Чек будет отправлен на указанную почту. Теперь ты можешь оплатить подписку:\n\n\nПри возникновении трудностей с оплатой обращайтесь к @tarot_manager",
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [InlineKeyboardButton(text=f"Купить расклад🔮 - {amount}₽", url=payment_url)],
                [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                text="Спасибо! Чек будет отправлен на указанную почту. Теперь ты можешь оплатить расклад:\n\n\nПри возникновении трудностей с оплатой обращайтесь к @tarot_manager",
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Ошибка при создании платежа в ЮKassa: {str(e)}")
        keyboard = [
            [InlineKeyboardButton(text="Попробовать снова🔄", callback_data=f"{payment_type}_info")],
            [InlineKeyboardButton(text="Назад⬅️", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            text="Произошла ошибка при генерации ссылки на оплату. Попробуй снова! 😔",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# Функция для настройки меню команд
async def set_bot_commands(application: Application):
    commands = [
        BotCommand(command="start", description="Выбрать расклад"),
        BotCommand(command="referral", description="Получить реферальную ссылку")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Меню команд успешно установлено: /start, /referral")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("referral", referral))  # Добавляем обработчик для /referral
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email))
    application.post_init = set_bot_commands

    logger.info("Настройка вебхука...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(application.bot.set_webhook(url="https://ai-girls.ru/webhook"))
    logger.info("Вебхук успешно установлен")

    logger.info("Запуск бота с вебхуком...")
    application.run_webhook(
        listen="0.0.0.0",
        port=8443,
        url_path="/webhook",
        webhook_url="https://ai-girls.ru/webhook"
    )

if __name__ == '__main__':
    main()