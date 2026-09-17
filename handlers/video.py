import asyncio
import logging
import shutil
import os
import time
from typing import Optional
from config import TEMP_DIR

# Настройка логирования
logger = logging.getLogger(__name__)

# Telegram жёстко ограничивает видеокружок 12 МиБ
MAX_VIDEO_NOTE_BYTES = 12 * 1024 * 1024
# Запас на служебные данные контейнера и неточность rate control
SIZE_SAFETY_RATIO = 0.92
# Вращающаяся обложка не выигрывает от высокой частоты кадров
VIDEO_FPS = 25
AUDIO_BITRATE_KBPS = 96
MIN_VIDEO_BITRATE_KBPS = 400
# Затухание: короткий фейд-аут, чтобы звук не обрывался кликом,
# но и не пропадал за секунду до конца ролика
FADE_IN_SEC = 3
FADE_OUT_SEC = 0.5
MAX_VIDEO_BITRATE_KBPS = 1800
# Сколько раз пробуем пережать, если файл всё же не влез в лимит
MAX_ENCODE_ATTEMPTS = 3

def check_ffmpeg_installed() -> bool:
    """Проверяет наличие ffmpeg в системе."""
    return shutil.which("ffmpeg") is not None

def build_ffmpeg_cmd(*args: str) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-loglevel", "error"] + list(args)

def calc_video_bitrate_kbps(duration: float) -> int:
    """Считает битрейт видео, при котором ролик укладывается в лимит Telegram."""
    if duration <= 0:
        return MIN_VIDEO_BITRATE_KBPS

    budget_bits = MAX_VIDEO_NOTE_BYTES * SIZE_SAFETY_RATIO * 8
    audio_bits = AUDIO_BITRATE_KBPS * 1000 * duration
    video_kbps = int((budget_bits - audio_bits) / duration / 1000)

    return max(MIN_VIDEO_BITRATE_KBPS, min(MAX_VIDEO_BITRATE_KBPS, video_kbps))

def build_encode_cmd(
    audio_path: str,
    cover_path: str,
    start_time: int,
    duration: float,
    video_bitrate_kbps: int,
    output_path: str
) -> list[str]:
    """Собирает команду ffmpeg для одной попытки кодирования."""
    fade_in_duration = min(FADE_IN_SEC, duration)              # Не более длительности самого аудио
    fade_out_duration = min(FADE_OUT_SEC, duration)
    fade_out_start = max(0, duration - fade_out_duration)

    return build_ffmpeg_cmd(
        "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", audio_path,
        "-loop", "1",
        "-i", cover_path,
        "-c:v", "libx264",
        "-vf", "scale=512:512:force_original_aspect_ratio=1,pad=512:512:(ow-iw)/2:(oh-ih)/2,rotate='angle=0.5*t:ow=512:oh=512',format=yuv420p",
        "-af", f"afade=t=in:st=0:d={fade_in_duration},afade=t=out:st={fade_out_start}:d={fade_out_duration}",
        "-c:a", "aac", "-b:a", f"{AUDIO_BITRATE_KBPS}k",
        "-b:v", f"{video_bitrate_kbps}k",
        "-maxrate", f"{int(video_bitrate_kbps * 1.15)}k",
        "-bufsize", f"{video_bitrate_kbps * 2}k",
        "-r", str(VIDEO_FPS),
        "-pix_fmt", "yuv420p",
        "-profile:v", "baseline",
        "-level", "4.2",
        "-movflags", "+faststart",
        "-map", "0:a:0",
        "-map", "1:v:0",
        # -shortest не обрезает видео из зацикленной картинки точно по звуку:
        # ролик получается на 1-2 секунды длиннее и хвост идёт без звука.
        # Ограничиваем длительность и на выходе.
        "-t", str(duration),
        "-shortest",
        output_path
    )

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

def remove_temp_video(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        os.remove(path)
        logger.info(f"Временный файл видео удалён: {path}")
    except Exception as e:
        logger.error(f"Ошибка удаления временного файла: {e}")

async def make_rotating_circle_video_bytes(
    audio_path: str,
    cover_path: str,
    start_time: int = 0,
    duration: float = 60
) -> Optional[bytes]:
    """Генерирует видео в формате видеокружка и возвращает bytes.

    Битрейт подбирается так, чтобы уложиться в лимит Telegram (12 МиБ);
    если файл всё же оказался больше, ролик пережимается заново.
    """
    if not check_ffmpeg_installed():
        logger.error("ffmpeg не установлен в системе.")
        return None

    if duration <= 0:
        logger.error(f"Некорректная длительность видео: {duration}")
        return None

    # Создаем уникальное имя для временного файла
    output_path = os.path.join(TEMP_DIR, f"video_{int(time.time() * 1000)}.mp4")
    video_bitrate_kbps = calc_video_bitrate_kbps(duration)

    logger.info(
        f"Генерация видео: аудио={audio_path}, обложка={cover_path}, "
        f"длительность={duration} сек, битрейт={video_bitrate_kbps}k"
    )

    try:
        for attempt in range(1, MAX_ENCODE_ATTEMPTS + 1):
            cmd = build_encode_cmd(
                audio_path, cover_path, start_time, duration,
                video_bitrate_kbps, output_path
            )

            success, _ = await run_ffmpeg(cmd)
            if not success:
                return None

            try:
                size = os.path.getsize(output_path)
            except OSError as e:
                logger.error(f"Не удалось определить размер видеофайла: {e}")
                return None

            logger.info(
                f"Попытка {attempt}: размер видео {size} байт "
                f"при битрейте {video_bitrate_kbps}k"
            )

            if size <= MAX_VIDEO_NOTE_BYTES:
                try:
                    with open(output_path, "rb") as f:
                        video_bytes = f.read()
                    logger.info("Видео успешно сгенерировано")
                    return video_bytes
                except Exception as e:
                    logger.error(f"Ошибка чтения видеофайла: {e}")
                    return None

            # Файл не влез — пересчитываем битрейт по фактическому перевесу
            target_bytes = MAX_VIDEO_NOTE_BYTES * SIZE_SAFETY_RATIO
            next_bitrate = max(
                MIN_VIDEO_BITRATE_KBPS,
                int(video_bitrate_kbps * target_bytes / size)
            )

            if next_bitrate >= video_bitrate_kbps:
                logger.error(
                    f"Видео не укладывается в лимит даже при {video_bitrate_kbps}k"
                )
                return None

            logger.warning(
                f"Видео превысило лимит ({size} > {MAX_VIDEO_NOTE_BYTES}), "
                f"пережимаем при {next_bitrate}k"
            )
            video_bitrate_kbps = next_bitrate

        logger.error(
            f"Не удалось уложиться в лимит за {MAX_ENCODE_ATTEMPTS} попытки"
        )
        return None
    finally:
        # Всегда удаляем временный файл
        remove_temp_video(output_path)
