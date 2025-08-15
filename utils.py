import os
import asyncio
import logging
import io
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from aiogram.types import Message, BufferedInputFile
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from PIL import Image, UnidentifiedImageError
from config import TEMP_DIR, DEFAULT_COVER
from video import make_rotating_circle_video_bytes

# Создаем временную директорию если не существует
def ensure_temp_dir():
    """Создает временную директорию если не существует"""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        logging.info(f"Создана временная директория: {TEMP_DIR}")
    else:
        logging.info(f"Временная директория уже существует: {TEMP_DIR}")

# Сохраняем аудиофайл из сообщения
async def save_audio(message: Message) -> str:
    # Поддерживаемые MIME-типы
    mime_types = ["audio/mpeg", "audio/mp4", "audio/x-m4a"]
    
    if message.document and message.document.mime_type in mime_types:
        file_id = message.document.file_id
        unique_id = message.document.file_unique_id
        # Определяем расширение файла по MIME-типу
        if message.document.mime_type == "audio/mpeg":
            ext = ".mp3"
        else:  # audio/mp4 или audio/x-m4a
            ext = ".m4a"
    elif message.audio:
        file_id = message.audio.file_id
        unique_id = message.audio.file_unique_id
        # Для аудиосообщений используем MP3 по умолчанию
        ext = ".mp3"
    else:
        raise ValueError("Поддерживаются только mp3 и m4a файлы.")

    file_path = os.path.join(TEMP_DIR, f"{unique_id}{ext}")
    
    try:
        # Получаем информацию о файле
        file = await message.bot.get_file(file_id)
        # Загружаем файл
        await message.bot.download_file(file.file_path, destination=file_path)
        
        logging.info(f"Аудио сохранено: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Ошибка при загрузке аудио: {e}")
        raise RuntimeError("Не удалось загрузить аудиофайл")

# Извлекаем обложку из аудиофайла
async def extract_cover(audio_path: str) -> str | None:
    try:
        # Определяем формат по расширению
        ext = os.path.splitext(audio_path)[1].lower()
        cover_data = None
        
        # Обработка MP3
        if ext == '.mp3':
            audio = MP3(audio_path, ID3=ID3)
            if not audio.tags:
                logging.info(f"Метаданные не найдены в файле: {audio_path}")
                return None
                
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    cover_data = tag.data
                    break
        
        # Обработка M4A
        elif ext == '.m4a':
            audio = MP4(audio_path)
            if 'covr' not in audio:
                return None
                
            cover_data = audio['covr'][0]
            if isinstance(cover_data, MP4Cover):
                cover_data = cover_data.data
        
        # Неподдерживаемый формат
        else:
            logging.warning(f"Неподдерживаемый формат: {audio_path}")
            return None
        
        if not cover_data:
            return None
            
        cover_path = os.path.join(TEMP_DIR, f"meta_cover_{os.path.basename(audio_path)}.jpg")
        
        # Проверяем валидность изображения
        try:
            img = Image.open(io.BytesIO(cover_data))
            img.verify()
            img.close()
        except (UnidentifiedImageError, OSError) as e:
            logging.warning(f"Обложка повреждена: {e}")
            return None
        
        with open(cover_path, "wb") as img_file:
            img_file.write(cover_data)
        
        logging.info(f"Обложка извлечена: {cover_path}")
        return cover_path
        
    except Exception as e:
        logging.error(f"Ошибка извлечения обложки: {e}")
        return None

# Сохраняем пользовательскую обложку
async def save_cover(message: Message) -> str:
    photo = message.photo[-1]  # Берем самое качественное фото
    file_id = photo.file_id
    unique_id = photo.file_unique_id
    file_path = os.path.join(TEMP_DIR, f"{unique_id}.jpg")
    
    try:
        # Получаем информацию о файле
        file = await message.bot.get_file(file_id)
        # Загружаем файл
        await message.bot.download_file(file.file_path, destination=file_path)
        
        logging.info(f"Обложка сохранена: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Ошибка при загрузке обложки: {e}")
        raise RuntimeError("Не удалось загрузить обложку")

# Обрезаем аудио до 60 секунд
async def cut_audio_async(audio_path: str, start_sec: int) -> str:
    # Восстанавливаем оригинальное имя файла с правильным расширением
    base_name = os.path.basename(audio_path)
    name, ext = os.path.splitext(base_name)
    output_path = os.path.join(TEMP_DIR, f"cut_{name}{ext}")
    
    cmd = [
        "ffmpeg", "-y", 
        "-ss", str(start_sec), 
        "-i", audio_path,
        "-t", "60", 
        "-c", "copy",  # Используем копирование без перекодировки
        output_path
    ]
    
    logging.info(f"Выполнение команды обрезки: {' '.join(cmd)}")
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE
    )
    
    _, stderr = await proc.communicate()
    
    if proc.returncode == 0:
        logging.info(f"Аудио обрезано: {output_path}")
        return output_path
    else:
        error_msg = stderr.decode() if stderr else "Неизвестная ошибка"
        logging.error(f"Ошибка обрезки аудио: {error_msg}")
        raise RuntimeError(f"Ошибка обрезки аудио: {error_msg}")

# Проверяем подписку пользователя
async def is_user_subscribed(bot: Bot, user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest:
        logging.warning(f"Проверка подписки не удалась для пользователя {user_id}")
        return False
    except Exception as e:
        logging.error(f"Ошибка при проверке подписки: {e}")
        return False

# Удаляем временные файлы
async def remove_temp_file(path: str):
    try:
        if path and os.path.exists(path) and path != DEFAULT_COVER:
            os.remove(path)
            logging.info(f"Файл удалён: {path}")
    except Exception as e:
        logging.error(f"Ошибка удаления файла {path}: {e}")

# Получаем метаданные трека
def get_track_metadata(audio_path: str) -> dict:
    try:
        # Определяем формат по расширению
        ext = os.path.splitext(audio_path)[1].lower()
        
        if ext == '.mp3':
            audio = MP3(audio_path, ID3=ID3)
            return {
                "artist": audio.get("TPE1").text[0] if "TPE1" in audio else "",
                "title": audio.get("TIT2").text[0] if "TIT2" in audio else ""
            }
        elif ext == '.m4a':
            audio = MP4(audio_path)
            return {
                "artist": audio.get("\xa9ART", [""])[0],
                "title": audio.get("\xa9nam", [""])[0]
            }
        else:
            return {"artist": "", "title": ""}
    except Exception as e:
        logging.error(f"Ошибка получения метаданных: {e}")
        return {"artist": "", "title": ""}

# Конвертируем обложку в квадрат 512x512
async def convert_to_square(image_path: str) -> str:
    """Гарантирует квадратный формат 512x512 с сохранением пропорций"""
    try:
        # Проверяем, не является ли изображение уже квадратным
        with Image.open(image_path) as img:
            if img.size == (512, 512) and img.mode == "RGB":
                logging.info(f"Обложка уже квадратная: {image_path}")
                return image_path

        # Создаем новое квадратное изображение
        output_path = os.path.join(TEMP_DIR, f"square_{os.path.basename(image_path)}")
        img = Image.open(image_path).convert("RGB")
        img = img.resize((512, 512), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=90)
        logging.info(f"Обложка преобразована в квадрат: {output_path}")
        
        # Удаляем оригинал если это не дефолтная обложка
        if image_path != DEFAULT_COVER:
            await remove_temp_file(image_path)
            
        return output_path
    except Exception as e:
        logging.error(f"Ошибка конвертации в квадрат: {e}")
        return image_path

# Отправляем результат пользователю
async def send_result(message: Message, state):
    try:
        data = await state.get_data()
        audio_path = data.get("audio_path")
        cover_path = data.get("cover_path") or DEFAULT_COVER
        start_time = data.get("start_time", 0)
        
        if not audio_path or not os.path.exists(audio_path):
            logging.error("Аудиофайл не найден")
            await message.answer("❌ Ошибка: аудиофайл не найден")
            return
        
        logging.info(f"Генерация видеокружка для: audio={audio_path}, cover={cover_path}")

        # Определяем длительность трека
        try:
            audio = MP3(audio_path)
            duration = min(60, audio.info.length)
        except Exception as e:
            logging.error(f"Ошибка получения длительности: {e}")
            duration = 60

        # Преобразуем обложку в квадрат
        if cover_path and cover_path != DEFAULT_COVER and os.path.exists(cover_path):
            square_cover = await convert_to_square(cover_path)
        else:
            square_cover = DEFAULT_COVER

        # Генерируем видеокружок
        video_bytes = await make_rotating_circle_video_bytes(
            audio_path=audio_path,
            cover_path=square_cover,
            start_time=start_time,
            duration=duration
        )
        
        # Отправляем результат
        if video_bytes:
            video_file = BufferedInputFile(video_bytes, filename="video_note.mp4")
            await message.answer_video_note(video_file)
        else:
            raise RuntimeError("Ошибка генерации видеокружка")
        
        # Очищаем временные файлы
        await cleanup_temp_files(audio_path, square_cover)
    except Exception as e:
        logging.exception("Критическая ошибка в send_result:")
        await message.answer("❌ Произошла непредвиденная ошибка. Пожалуйста, попробуйте ещё раз.")

# Очищаем временные файлы
async def cleanup_temp_files(audio_path: str, cover_path: str):
    try:
        # Удаляем основной аудиофайл
        if audio_path and os.path.exists(audio_path):
            await remove_temp_file(audio_path)
        
        # Удаляем обложку если она не дефолтная
        if cover_path != DEFAULT_COVER and cover_path and os.path.exists(cover_path):
            await remove_temp_file(cover_path)
        
        # Удаляем производные файлы
        if audio_path:
            base_name = os.path.basename(audio_path)
            base_prefix = base_name.split('.')[0]
            
            for file in os.listdir(TEMP_DIR):
                if file.startswith(base_prefix) and file != base_name:
                    file_path = os.path.join(TEMP_DIR, file)
                    if os.path.isfile(file_path) and not file.endswith(".mp4"):
                        await remove_temp_file(file_path)
    except Exception as e:
        logging.error(f"Ошибка очистки временных файлов: {e}")