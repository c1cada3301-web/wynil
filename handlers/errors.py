"""Перевод исключений в понятные пользователю сообщения.

В лог по-прежнему уходит полная трассировка, пользователю — короткое
объяснение и код, по которому эту ошибку можно найти в логе.
"""
import asyncio
import logging
import uuid
from typing import Optional

from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

try:
    from aiogram.exceptions import TelegramEntityTooLarge
except ImportError:  # На старых версиях aiogram этого класса нет
    class TelegramEntityTooLarge(Exception):
        pass

logger = logging.getLogger(__name__)

TOO_LARGE_MESSAGE = (
    "❌ Видеокружок получился слишком большим для Telegram.\n\n"
    "Попробуйте выбрать другой фрагмент трека или обложку попроще."
)
VOICE_FORBIDDEN_MESSAGE = (
    "❌ Не удалось отправить видеокружок.\n\n"
    "У вас в настройках Telegram запрещена отправка голосовых сообщений и кружков.\n"
    "Разрешите их: Настройки → Конфиденциальность → Голосовые сообщения."
)
NETWORK_MESSAGE = (
    "❌ Telegram сейчас не отвечает.\n\n"
    "Подождите минуту и попробуйте ещё раз — трек никуда не денется."
)
DOWNLOAD_MESSAGE = (
    "❌ Не получилось скачать файл из Telegram.\n\n"
    "Отправьте его, пожалуйста, ещё раз."
)
FORMAT_MESSAGE = (
    "❌ Такой файл я обработать не смогу.\n\n"
    "Нужен аудиофайл mp3 или m4a."
)
BROKEN_AUDIO_MESSAGE = (
    "❌ Не удалось прочитать этот аудиофайл — похоже, он повреждён.\n\n"
    "Попробуйте другой файл."
)
FFMPEG_MESSAGE = (
    "❌ На сервере не настроен обработчик видео.\n\n"
    "Это моя поломка, а не ваша. Попробуйте позже."
)
GENERATION_MESSAGE = (
    "❌ Не получилось собрать кружок из этого фрагмента.\n\n"
    "Попробуйте другую точку обрезки или другой трек."
)
IMAGE_MESSAGE = (
    "❌ С этой картинкой я не справился.\n\n"
    "Пришлите другое изображение — обычный jpg или png."
)
FALLBACK_MESSAGE = (
    "❌ Что-то сломалось на моей стороне.\n\n"
    "Попробуйте ещё раз. Если повторится — пришлите нам код ошибки: {code}"
)

def describe_error(error: BaseException) -> Optional[str]:
    """Подбирает понятное сообщение по ошибке. None — если причина неизвестна."""
    text = str(error)
    lowered = text.lower()

    if isinstance(error, TelegramEntityTooLarge):
        return TOO_LARGE_MESSAGE

    if isinstance(error, TelegramBadRequest):
        if "too large" in lowered or "request entity too large" in lowered:
            return TOO_LARGE_MESSAGE
        if "VOICE_MESSAGES_FORBIDDEN" in text:
            return VOICE_FORBIDDEN_MESSAGE
        return None

    if isinstance(error, (TelegramNetworkError, asyncio.TimeoutError)):
        return NETWORK_MESSAGE

    if isinstance(error, ValueError) and ("mp3" in lowered or "m4a" in lowered):
        return FORMAT_MESSAGE

    if "не удалось загрузить аудиофайл" in lowered:
        return DOWNLOAD_MESSAGE
    if "не удалось загрузить обложку" in lowered:
        return IMAGE_MESSAGE
    if "ffmpeg" in lowered:
        return FFMPEG_MESSAGE
    if "обрезки аудио" in lowered:
        return BROKEN_AUDIO_MESSAGE

    return None

def report_error(context: str, error: BaseException, fallback: Optional[str] = None) -> str:
    """Пишет подробности в лог и возвращает текст для пользователя.

    context — где сломалось, попадает только в лог.
    fallback — сообщение для случая, когда причина не распознана.
    """
    code = uuid.uuid4().hex[:6]
    logger.exception(f"[{code}] {context}: {type(error).__name__}: {error}")

    known = describe_error(error)
    if known:
        return known

    return (fallback or FALLBACK_MESSAGE).replace("{code}", code)
