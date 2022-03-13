import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

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
logging.basicConfig(
    filename='log.log',
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправляет сообщение о статусе работы."""
    logger.info(f'Отправляю сообщение:{message}')
    send = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """Делает API запрос."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    logging.info('Сервер работает')
    if homework_statuses.status_code != 200:
        raise Exception('Сервер не работает')
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ сервера."""
    homeworks = response['homeworks']
    if 'homeworks' not in response:
        logger.error('Not found key homeworks')
        raise AssertionError('Ключи отсутсвуют')
    elif 'current_date' not in response:
        logger.error('Not found key current_date')
        raise AssertionError('Ключи отсутсвуют')
    elif type(response['homeworks']) is not list:
        raise TypeError('API возвращает не список')
    else:
        logger.info('Все ок')
    return homeworks


def parse_status(homework):
    """Извлекает статус работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_status not in HOMEWORK_STATUSES:
        print(f'Неизвестный стаутс:{homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет доступность окружения, необходимое для работы программы."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Переменных нет')
        raise SystemExit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)

            homeworks = check_response(response)
            if isinstance(homeworks, list):
                send_message(bot, parse_status(homeworks[0]))
            else:
                logger.info('Домашней работы нет')

            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)
            send_message(bot, message)
        else:
            print('Выход из программы')
            sys.exit(0)


if __name__ == '__main__':
    main()
