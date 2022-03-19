import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (TelegramException, PracticumNotWork,
                        TokensNotFound)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def send_message(bot, message):
    """Отправляет сообщение о статусе работы."""
    logger.info(f'Отправляю сообщение:{message}')
    send = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    if not send:
        logger.error('Ошибка Telegram, сообщение не отправлено')
        raise TelegramException('Не могу отправить сообщение')


def get_api_answer(current_timestamp):
    """Делает API запрос."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logger.info('Сервер работает')
        if homework_statuses.status_code != HTTPStatus.OK:
            raise PracticumNotWork('Сервер не работает')
    except Exception as error:
        logger.error(error)
        raise PracticumNotWork('Ошибка сервера')
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ сервера."""
    if not isinstance(response, dict):
        logger.error('Это не словарь')
        raise TypeError('API возвращает не словарь')
    homeworks = response.get('homeworks')
    if 'current_date' not in response:
        logger.error('Not found key current_date')
        raise KeyError('Ключи отсутсвуют')
    elif 'homeworks' not in response:
        logger.error('Not found key homeworks')
        raise KeyError('Ключи отсутсвуют')
    elif not isinstance(response['homeworks'], list):
        raise TypeError('API возвращает не список')
    return homeworks


def parse_status(homework):
    """Извлекает статус работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name and homework_status is None:
        raise KeyError
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'Неизвестный стаутс:{homework_status}')
        raise KeyError
    else:
        verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет доступность окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Переменных нет')
        raise TokensNotFound()
        sys.exit('Переменных нет')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            try:
                homework = check_response(response)
                send_message(bot, parse_status(homework[0]))
            except:
                logging.info('Домашней работы нет')

            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
    logging.basicConfig(
        filename='log.log',
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    )
    logger.addHandler(logging.StreamHandler())
