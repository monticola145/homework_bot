import logging
import os
import time
import sys
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot
import telegram

import exceptions

NotForSending = exceptions.NotForSending
IsForSending = exceptions.IsForSending
EmptyAPIAnswer = exceptions.EmptyAPIAnswer
WrongResponseCode = exceptions.WrongResponseCode

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

logging.basicConfig(
    # handlers=[logging.StreamHandler()],
    # никак не могу справиться со StreamHandler
    # без него всё работает
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(funcName)s, %(message)s',
    encoding='UTF-8',
    filemode='w'
)
# и если прятать там же, где и main()

logger = logging.getLogger(__name__)
# если это удалить, то всё ломается


def send_message(bot, message):
    """Функция отправки сообщений."""
    try:
        logger.info('Отправка сообщения...')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError(NotForSending) as error:
        raise error(f'Сбой при отправке сообщения в Telegram: {error}')
        #  так?
    else:
        logger.info('Сообщение успешно отправлено')


def get_api_answer(current_timestamp):
    """Функция связи с API."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    headers = HEADERS
    # со словарём не понял:
    # dict = dict(params={'from_date': timestamp}, headers=HEADERS)
    # а потом:
    # response = requests.get(ENDPOINT, headers=dict.keys('headers'),
    # params=dict.keys('params'))
    # ?
    try:
        response = requests.get(ENDPOINT, headers=headers, params=params)
        logger.info('Запос к API...')
        if response.status_code != HTTPStatus.OK:
            raise WrongResponseCode(
                f'Код:{response.status_code}/{response.text}'
            )
        else:
            return response.json()
    except ConnectionError as error:
        raise error(
            'Тут я распаковываю гипотетический словарь,\
            приведённый сверху в #?')


def check_response(response):
    """Функция проверки ответа API."""
    logger.info('Гачало проверки ответа API...')
    if not isinstance(response, dict):
        raise TypeError('API != dict')
    if ['homeworks'][0] not in response:
        raise EmptyAPIAnswer('Такой домашки нет')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise KeyError('API != list')
    else:
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
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    #  return (f'Изменился статус проверки работы "{per1}{per2}"'.format(
    #  per1=homework_name, per2=HOMEWORK_VERDICTS[homework_status]))
    #  так?


def check_tokens():
    """Функция проверки наличия токенов."""
    if all([PRACTICUM_TOKEN and TELEGRAM_TOKEN]):
        return True
    else:
        logging.critical('Отсутствие ожидаемых ключей в ответе API')
        return False
    # ещё видел такой вариант:
    # tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN]
    # return None not in vars


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logger.critical('Токены не найдены!')
        sys.exit(1)
        # прочитал инфу по ссылке, но не очень понял
        # поищу ещё в интернете
        # пока так
    else:
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        current_report = {'name': 'message'}
        prev_report = {'name': 'message'}
        while True:
            try:
                response = get_api_answer(current_timestamp)
                # вот тут не понял про дату и умолчательное
                homework = check_response(response)
                if homework:
                    homework = response.get('homeworks')[0]
                    message = parse_status(homework)
                    current_report[homework['name']] = message
                    if message is not None:
                        if current_report != prev_report:
                            send_message(bot, message)
                            prev_report = current_report.copy()
                else:
                    current_report[homework['name']] = 'Нет новых статусов'
                    logging.info('Нет новых статусов')
                # так?
                time.sleep(RETRY_TIME)
            except (EmptyAPIAnswer,
                    NotForSending) as error:
                logging.debug(f'Ошибка не для пересылки: {error}')

            except Exception:
                logging.critical('Сбой запуска программы')
                current_report[homework['name']] = 'Сбой запуска программы'
                if current_report != prev_report:
                    send_message(bot, message)
                    prev_report = current_report.copy()
            finally:
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main(), logging
    # так прятать?
