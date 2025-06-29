import logging
import asyncio
import os
import tempfile
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import API_TOKEN
from handlers import router as handlers_router
from db import init_db
from utils import ensure_temp_dir

API_TOKEN = os.getenv("API_TOKEN") or API_TOKEN

async def make_rotating_circle_video_bytes(audio_path, cover_path, start_time=0, duration=60):
    """
    Генерирует mp4-видеокружок с помощью ffmpeg, возвращает bytes.
    Длительность всегда ровно duration секунд.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_time),
        '-t', str(duration),
        '-i', audio_path,
        '-loop', '1', '-i', cover_path,
        '-c:v', 'libx264',
        '-vf', f"scale=512:512,rotate='angle=0.5*t:ow=512:oh=512',format=yuv420p",
        '-af', f"apad=pad_dur={duration},afade=in:st=0:d=3,afade=out:st={duration-3}:d=3",
        '-c:a', 'aac',
        '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'baseline',
        '-level', '3.0',
        '-fs', '7M',
        '-map', '0:a:0',
        '-map', '1:v:0',
        # '-shortest',  # Не используем!
        tmp_path
    ]
    logging.info(f"Команда ffmpeg для видео (bytes): {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode == 0:
        with open(tmp_path, "rb") as f:
            video_bytes = f.read()
        os.remove(tmp_path)
        logging.info("ffmpeg успешно создал видео (bytes)")
        return video_bytes
    else:
        logging.error(f"ffmpeg ошибка: {stderr.decode()}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return None

async def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("Создание временной директории...")
    ensure_temp_dir()
    logger.info("Создание экземпляра бота и диспетчера...")

    bot = Bot(
        token=API_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем только корневой роутер, который включает всю инфраструктуру
    dp.include_router(handlers_router)

    try:
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен пользователем")
    except Exception as e:
        print(f"Необработанная ошибка: {e}")