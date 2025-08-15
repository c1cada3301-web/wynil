import asyncio
import logging
import shutil
import os
import time
from typing import Optional
from config import TEMP_DIR

# Настройка логирования
logger = logging.getLogger(__name__)

def check_ffmpeg_installed() -> bool:
    """Проверяет наличие ffmpeg в системе."""
    return shutil.which("ffmpeg") is not None

def build_ffmpeg_cmd(*args: str) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-loglevel", "error"] + list(args)

async def run_ffmpeg(cmd: list[str]) -> tuple[bool, Optional[bytes]]:
    logger.info(f"Команда ffmpeg: {' '.join(cmd)}")
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Читаем stderr в реальном времени
    stderr_chunks = []
    while True:
        chunk = await proc.stderr.read(4096)
        if not chunk:
            break
        stderr_chunks.append(chunk)
    
    # Дожидаемся завершения процесса
    return_code = await proc.wait()
    
    if return_code == 0:
        logger.info("ffmpeg успешно завершил работу.")
        return True, None
    else:
        error_msg = b''.join(stderr_chunks).decode().strip()
        logger.error(f"ffmpeg ошибка: {error_msg}")
        return False, None

async def make_rotating_circle_video_bytes(
    audio_path: str,
    cover_path: str,
    start_time: int = 0,
    duration: int = 60
) -> Optional[bytes]:
    """Генерирует видео в формате видеокружка и возвращает bytes"""
    if not check_ffmpeg_installed():
        logger.error("ffmpeg не установлен в системе.")
        return None

    # Создаем уникальное имя для временного файла
    output_path = os.path.join(TEMP_DIR, f"video_{int(time.time() * 1000)}.mp4")
    
    # Рассчитываем параметры затухания аудио
    fade_in_duration = min(3, duration)  # Не более длительности самого аудио
    fade_out_start = max(0, duration - 3)  # Начинаем затухание за 3 секунды до конца
    
    # Формируем команду ffmpeg (рабочая версия)
    cmd = build_ffmpeg_cmd(
        "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", audio_path,
        "-loop", "1", 
        "-i", cover_path,
        "-c:v", "libx264",
        "-vf", "scale=512:512:force_original_aspect_ratio=1,pad=512:512:(ow-iw)/2:(oh-ih)/2,rotate='angle=0.5*t:ow=512:oh=512',format=yuv420p",
        "-af", f"afade=t=in:st=0:d={fade_in_duration},afade=t=out:st={fade_out_start}:d=3",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-profile:v", "baseline",
        "-level", "4.2",
        "-movflags", "+faststart",
        "-map", "0:a:0",
        "-map", "1:v:0",
        "-shortest",
        output_path
    )
    
    logger.info(f"Генерация видео: аудио={audio_path}, обложка={cover_path}, длительность={duration} сек")
    
    success, _ = await run_ffmpeg(cmd)
    
    if success:
        try:
            with open(output_path, "rb") as f:
                video_bytes = f.read()
            logger.info("Видео успешно сгенерировано")
            return video_bytes
        except Exception as e:
            logger.error(f"Ошибка чтения видеофайла: {e}")
            return None
        finally:
            # Всегда удаляем временный файл
            try:
                os.remove(output_path)
                logger.info(f"Временный файл видео удалён: {output_path}")
            except Exception as e:
                logger.error(f"Ошибка удаления временного файла: {e}")
    else:
        # Удаляем файл в случае ошибки
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                logger.info(f"Временный файл видео удалён после ошибки: {output_path}")
            except Exception as e:
                logger.error(f"Ошибка удаления временного файла: {e}")
        return None