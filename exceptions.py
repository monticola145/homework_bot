class NotForSending(Exception):
    """Ошибки, о которых не пишется в Telegram."""

    pass


class IsForSending(Exception):
    """Ошибки, о которых уведомляется в Telegram"""

    pass


class EmptyAPIAnswer(NotForSending):

    pass


class WrongResponseCode(IsForSending):

    pass


class TelegramError(NotForSending):

    pass
