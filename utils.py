import os
import asyncio
import logging
from video import prepare_cover, make_rotating_circle_video_bytes
from aiogram.types import Message, BufferedInputFile
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from config import TEMP_DIR, DEFAULT_COVER

def ensure_temp_dir():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

async def save_audio(message: Message) -> str:
    if message.document and message.document.mime_type == "audio/mpeg":
        file_id = message.document.file_id
        unique_id = message.document.file_unique_id
    elif message.audio:
        file_id = message.audio.file_id
        unique_id = message.audio.file_unique_id
    else:
        raise ValueError("Только mp3-файлы поддерживаются.")

    file_path = os.path.join(TEMP_DIR, unique_id + ".mp3")
    try:
        await message.bot.download(
            file=file_id,
            destination=file_path,
            timeout=120
        )
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла: {e}")
        await message.answer("Ошибка при загрузке файла. Попробуйте ещё раз или отправьте меньший файл.")
        raise
    return file_path

async def extract_cover(audio_path: str) -> str | None:
    audio = MP3(audio_path, ID3=ID3)
    cover_path = None
    for tag in audio.tags.values():
        if isinstance(tag, APIC):
            cover_path = os.path.join(TEMP_DIR, "cover_" + os.path.basename(audio_path) + ".jpg")
            with open(cover_path, "wb") as img:
                img.write(tag.data)
            break
    return cover_path

async def save_cover(message: Message) -> str:
    photo = message.photo[-1]
    file_id = photo.file_id
    unique_id = photo.file_unique_id
    file_path = os.path.join(TEMP_DIR, unique_id + ".jpg")
    try:
        await message.bot.download(
            file=file_id,
            destination=file_path,
            timeout=120
        )
    except Exception as e:
        logging.error(f"Ошибка при загрузке фото: {e}")
        await message.answer("Ошибка при загрузке фото. Попробуйте ещё раз или отправьте другое изображение.")
        raise
    return file_path

async def cut_audio_async(audio_path: str, start_sec: int) -> str:
    output_path = os.path.join(TEMP_DIR, f"cut_{os.path.basename(audio_path)}")
    cmd = [
        "ffmpeg", "-y", "-ss", str(start_sec), "-i", audio_path,
        "-t", "30", "-c", "copy", output_path
    ]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.communicate()
    return output_path

async def make_video_async(audio_path: str, cover_path: str, start_time: int = 0) -> str:
    output_path = os.path.join(TEMP_DIR, f"video_{os.path.basename(audio_path)}.mp4")
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_time),
        '-t', '60',
        '-i', audio_path,
        '-loop', '1', '-i', cover_path,
        '-c:v', 'libx264',
        '-vf', "scale=512:512,rotate='angle=0.5*t:ow=512:oh=512'",
        '-af', "afade=in:st=0:d=3,afade=out:st=57:d=3",
        '-c:a', 'aac',
        '-b:a', '128k',
        '-fs', '7M',
        '-map', '0:a:0',
        '-map', '1:v:0',
        output_path
    ]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.communicate()
    return output_path

async def is_user_subscribed(bot: Bot, user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest:
        logging.warning(f"Проверка подписки не удалась для пользователя {user_id}.")
        return False
    except Exception as e:
        logging.error(f"Ошибка при проверке подписки: {e}")
        return False

async def remove_temp_file(path: str):
    try:
        os.remove(path)
    except Exception:
        pass

def get_track_metadata(audio_path: str) -> dict:
    audio = MP3(audio_path, ID3=ID3)
    artist = audio.get("TPE1")
    title = audio.get("TIT2")
    return {
        "artist": artist.text[0] if artist else "",
        "title": title.text[0] if title else ""
    }

async def send_result(message: Message, state):
    data = await state.get_data()
    audio_path = data.get("audio_path") or data.get("mp3_path")
    cover_path = data.get("final_cover") or data.get("cover_path") or DEFAULT_COVER
    video_bytes = await make_rotating_circle_video_bytes(
        audio_path=audio_path,
        cover_path=cover_path,
        start_time=0,
        duration=60
    )
    if video_bytes:
        video_file = BufferedInputFile(video_bytes, filename="video.mp4")
        await message.answer_video_note(video_file)
    else:
        await message.answer("Произошла ошибка при генерации видео.")

async def audio_to_ogg(input_path: str, output_path: str, start_time: int = 0, duration: int = 60) -> bool:
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_time),
        '-t', str(duration),
        '-i', input_path,
        '-c:a', 'libopus',
        '-b:a', '128k',
        output_path
    ]
    logging.info(f"Команда ffmpeg для ogg: {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode == 0:
        logging.info(f"ffmpeg успешно создал ogg: {output_path}")
        return True
    else:
        logging.error(f"ffmpeg ошибка ogg: {stderr.decode()}")
        return False

import tempfile

async def make_rotating_circle_video_bytes(audio_path, cover_path, start_time=0, duration=60):
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_time),
        '-t', str(duration),
        '-i', audio_path,
        '-loop', '1', '-i', cover_path,
        '-c:v', 'libx264',
        '-vf', "scale=512:512,rotate='angle=0.5*t:ow=512:oh=512',format=yuv420p",
        '-af', f"apad=pad_dur={duration},afade=in:st=0:d=3,afade=out:st={duration-5}:d=5",
        '-c:a', 'aac',
        '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'baseline',
        '-level', '3.0',
        '-fs', '7M',
        '-map', '0:a:0',
        '-map', '1:v:0',
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