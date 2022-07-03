import logging
import os
import time
import sys
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot


import exceptions

NotForSending = exceptions.NotForSending
IsForSending = exceptions.IsForSending
EmptyAPIAnswer = exceptions.EmptyAPIAnswer
WrongResponseCode = exceptions.WrongResponseCode
TelegramError = exceptions.TelegramError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправки сообщений."""
    try:
        logging.info('Отправка сообщения...')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError as error:
        raise TelegramError(f'Сбой при отправке сообщения в Telegram: {error}')

    else:
        logging.info('Сообщение успешно отправлено')


def get_api_answer(current_timestamp):
    """Функция связи с API."""
    REPORT = ("Endpoint: {url} "
              "Headers: {headers} "
              "Parameters: {params}")

    timestamp = current_timestamp
    response_parameters = {'url': ENDPOINT, 'headers': HEADERS,
                           'params': {'from_date': timestamp}}
    try:
        response = requests.get(**response_parameters)
        logging.info(f'Запрос к API: {REPORT.format(**response_parameters)}')
        if response.status_code != HTTPStatus.OK:
            raise WrongResponseCode(
                f'Код:{response.status_code}/{response.text}/{response.reason}'
            )
        return response.json()
    except Exception as error:
        raise ConnectionError(f'Ошибка подключения: {error}! Параметры:',
                              REPORT.format(**response_parameters))


def check_response(response):
    """Функция проверки ответа API."""
    logging.info('Начало проверки ответа API...')
    if not isinstance(response, dict):
        raise TypeError('API != dict')
    if ('homeworks' or 'current_date') not in response:
        raise EmptyAPIAnswer('Такой домашки нет')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise KeyError('API != list')
    return homework


def parse_status(homework):
    """Функция проверки статуса домашки."""
    statuses = ['status', 'homework_name']
    for status in statuses:
        if status not in homework:
            raise KeyError('Неизвестный статус домашки')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError('Неизвестный статус')
    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{HOMEWORK_VERDICTS[homework_status]}')


def check_tokens():
    """Функция проверки наличия токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Токены не найдены!')
        sys.exit('Программа остановлека: токены не обнаружены!')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_report = {'name': 'message'}
    prev_report = {'name': 'message'}
    while True:
        try:
            response = get_api_answer(current_timestamp)
            response = response.get('current_date', current_timestamp)
            homework = check_response(response)
            if homework:
                homeworks = response.get('homeworks')
                homework = homeworks[0]
                print(homework)
                current_report['name'] = homework['homework_name']
                message = parse_status(homework)
                current_report['message'] = message
            else:
                current_report[homework[
                    'homework_name']] = 'Нет новых статусов'
            if current_report != prev_report:
                send_message(bot, message)
                prev_report = current_report.copy()
            else:
                logging.info('Новых статусов нет')
        except (NotForSending) as error:
            logging.error(f'Ошибка не для пересылки: {error}')

        except Exception as error:
            logging.exception(f'Сбой запуска программы: {error}')
            current_report['message'] = 'Сбой запуска программы'
            if current_report != prev_report:
                send_message(bot, message)
                prev_report = current_report.copy()
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler('main.log', encoding='UTF-8')],
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(funcName)s, %(message)s, %(lineno)s')
    main()
