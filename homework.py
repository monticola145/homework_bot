import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot

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

logging.basicConfig(
    handlers=[logging.StreamHandler()],
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)
detected_errors = []


def send_message(bot, message):
    """Функция отправки сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение успешно отправлено')
    except Exception:
        logging.error('Сбой при отправке сообщения в Telegram')


def send_error(bot, message):
    """Отправляет информацию об ошибках."""
    logger.error(message)
    if message not in detected_errors:
        try:
            send_message(bot, message)
            detected_errors.append(message)
        except Exception:
            logger.info('Отправка сообщения не состоялась')


def get_api_answer(current_timestamp):
    """Функция связи с API."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    headers = HEADERS
    response = requests.get(ENDPOINT, headers=headers, params=params)
    try:
        if response.status_code != HTTPStatus.OK:
            raise Exception('Нет подключения к API')
            logging.error('Обнаружена недоступность эндпоинта')
    except Exception:
        raise Exception('Ошибка API')
        logging.error('Сбой при запросе к эндпоинту')
    return response.json()


def check_response(response):
    """Функция проверки ответа API."""
    if not isinstance(response, dict):
        raise TypeError('API != dict')
    if ['homeworks'][0] not in response:
        raise IndexError('Такой домашки нет')
        logging.error('Отсутствие ожидаемых ключей в ответе API')
    homework = response.get('homeworks')[0]
    return homework


def parse_status(homework):
    """Функция проверки статуса домашки."""
    statuses = ['status', 'homework_name']
    for status in statuses:
        if status not in homework:
            raise KeyError('Неизвестный статус домашки')
            logging.error('Недокументированный статус домашней работы')

    homework_name = homework['homework_name']
    homework_status = homework['status']

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверки наличия токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN is not None:
        return True
    else:
        logging.critical('Отсутствие ожидаемых ключей в ответе API')
        return False


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework is not None:
                message = parse_status(homework)
                if message is not None:
                    send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception:
            logging.critical('Сбой запуска программы')
            send_error(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
