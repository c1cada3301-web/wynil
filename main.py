import logging
import asyncio
import os
import sys
import time
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import API_TOKEN, TEMP_DIR
from handlers import setup_routers
from handlers.db import init_db
from handlers.utils import ensure_temp_dir
from concurrent.futures import ThreadPoolExecutor

BOT_API_TIMEOUT = 10

def _make_bot(token: str) -> Bot:
    # Telegram API ходит через прокси (VLESS) — берём из ALL_PROXY/HTTPS_PROXY.
    # aiogram/aiohttp не подхватывает эти переменные сами, проксируем явно.
    proxy = os.getenv("ALL_PROXY") or os.getenv("HTTPS_PROXY")
    session = AiohttpSession(proxy=proxy, timeout=BOT_API_TIMEOUT)
    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )

async def auto_cleanup_temp():
    while True:
        for filename in os.listdir("temp"):
            file_path = os.path.join("temp", filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Ошибка удаления {file_path}: {e}")
        print(f"Автоочистка temp завершена: {time.ctime()}")
        await asyncio.sleep(3 * 60 * 60)  # 3 часа

async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)

    logger.info("=== Запуск бота Winyl ===")
    logger.info(f"Текущая рабочая директория: {os.getcwd()}")
    logger.info(f"Путь к временной директории: {TEMP_DIR}")
    
    # Создаем временную директорию
    ensure_temp_dir()
    
    # Инициализация БД
    logger.info("Инициализация базы данных...")
    await init_db()
    
    # Создаем бота с дефолтными настройками
    logger.info("Создание экземпляра бота...")
    bot = _make_bot(API_TOKEN)
    if bot.session.proxy:
        logger.info(f"Используется прокси для Telegram API: {bot.session.proxy}")
    else:
        logger.info("Прокси для Telegram API не задан — используется прямое соединение")
    
    # Настраиваем диспетчер
    logger.info("Настройка диспетчера...")
    executor = ThreadPoolExecutor(max_workers=3)
    dp = Dispatcher(storage=MemoryStorage(), executor=executor)
    
    # Подключаем роутеры
    logger.info("Настройка роутеров...")
    router = setup_routers()
    dp.include_router(router)

    # Запускаем автоочистку временной директории
    asyncio.create_task(auto_cleanup_temp())

    # Запуск бота
    try:
        logger.info("=== Бот запущен и готов к работе ===")
        # Увеличиваем таймаут для long polling
        await dp.start_polling(bot, timeout=60)
    except asyncio.CancelledError:
        logger.info("Получен сигнал завершения работы")
    except Exception as e:
        logger.exception("Критическая ошибка в работе бота:")
        raise
    finally:
        logger.info("Завершение работы бота...")
        await bot.session.close()
        executor.shutdown(wait=True)
        logger.info("Ресурсы освобождены")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Необработанная ошибка: {e}")
        sys.exit(1)