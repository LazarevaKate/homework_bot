import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram
from telegram.error import NetworkError

from config import (
    TELEGRAM_CHAT_ID, ENDPOINT, HEADERS,
    HOMEWORK_STATUSES, PRACTICUM_TOKEN,
    TELEGRAM_TOKEN, RETRY_TIME,
)
from exceptions import PracticumNotWork, TokensNotFound


logger = logging.getLogger(__name__)


def send_message(bot, message):
    """Отправляет сообщение о статусе работы."""
    try:
        logger.info(f'Отправляю сообщение:{message}')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logger.error(f'{error}: Telegram, сообщение не отправлено')
        raise NetworkError('Не могу отправить сообщение')


def get_api_answer(current_timestamp):
    """Делает API запрос."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        logger.info('Сервер работает')
        if homework_statuses.status_code != HTTPStatus.OK:
            raise PracticumNotWork('Сервер не работает')
        elif homework_statuses.status_code == HTTPStatus.NOT_FOUND:
            raise TokensNotFound('Какая-то проблема со стороны клиента')
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
    if 'current_date' and 'homeworks' not in response:
        logger.error('Not found keys')
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
            except Exception as error:
                logging.info(f'Домашней работы нет: {error}')

            current_timestamp = response.get('current_date')

        except Exception as error:
            message = f'Сбой в работе программы, {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
    logging.basicConfig(
        filename='log.log',
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    )
    logger.addHandler(logging.StreamHandler())
