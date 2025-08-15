import logging
import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import API_TOKEN, TEMP_DIR
from handlers import setup_routers
from db import init_db
from utils import ensure_temp_dir
from concurrent.futures import ThreadPoolExecutor

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
    bot = Bot(
        token=API_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Настраиваем диспетчер
    logger.info("Настройка диспетчера...")
    executor = ThreadPoolExecutor(max_workers=3)
    dp = Dispatcher(storage=MemoryStorage(), executor=executor)
    
    # Подключаем роутеры
    logger.info("Настройка роутеров...")
    router = setup_routers()
    dp.include_router(router)
    
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