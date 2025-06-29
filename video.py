import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image

def check_ffmpeg_installed() -> bool:
    """
    Проверяет наличие ffmpeg в системе.
    """
    return shutil.which("ffmpeg") is not None

def build_ffmpeg_cmd(*args: str) -> list[str]:
    return ["ffmpeg"] + list(args)

async def run_ffmpeg(cmd: list[str], dry_run: bool = False) -> tuple[bool, Optional[bytes]]:
    logging.info(f"Команда ffmpeg: {' '.join(cmd)}")
    if dry_run:
        logging.info("Запущен dry_run: команда не будет выполнена.")
        return True, None

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode == 0:
        logging.info("ffmpeg успешно завершил работу.")
        return True, stdout
    else:
        logging.error(f"ffmpeg ошибка: {stderr.decode()}")
        logging.debug(f"ffmpeg stdout: {stdout.decode()}")
        return False, None

async def video_to_circle(
    temp_video_path: str,
    output_path: str,
    start_time: int = 0,
    duration: int = 60,
    size: int = 512,
    with_audio: bool = False,
    dry_run: bool = False
) -> bool:
    if not check_ffmpeg_installed():
        logging.error("ffmpeg не установлен в системе.")
        return False

    cmd = [
        "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", temp_video_path,
        "-vf", f"scale={size}:{size},crop={size}:{size},rotate='angle=0.5*t:ow={size}:oh={size}',fade=t=out:st={duration-3}:d=3",
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-profile:v", "baseline",
        "-level", "3.0",
        "-b:v", "800k",
        "-fs", "7M",
    ]

    if with_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-an"]

    cmd += [output_path]
    cmd = build_ffmpeg_cmd(*cmd)
    success, _ = await run_ffmpeg(cmd, dry_run=dry_run)
    return success

async def prepare_cover(cover_path: str, output_path: str, size: int = 512) -> str:
    try:
        img = Image.open(cover_path).convert("RGB")
        img = img.resize((size, size), Image.LANCZOS)
        img.save(output_path, "JPEG")
        logging.info(f"Обложка подготовлена: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Ошибка подготовки обложки: {e}")
        raise

async def make_rotating_circle_video(
    audio_path: str,
    cover_path: str,
    output_path: str,
    start_time: int = 0,
    duration: int = 60,
    dry_run: bool = False
) -> bool:
    if not check_ffmpeg_installed():
        logging.error("ffmpeg не установлен в системе.")
        return False

    prepared_cover = cover_path
    if not cover_path.lower().endswith("_512.jpg"):
        prepared_cover = cover_path.rsplit('.', 1)[0] + "_512.jpg"
        await prepare_cover(cover_path, prepared_cover, 512)

    cmd = build_ffmpeg_cmd(
        "-y", "-ss", str(start_time), "-t", str(duration),
        "-i", audio_path,
        "-loop", "1", "-i", prepared_cover,
        "-c:v", "libx264",
        "-vf", "scale=512:512,rotate='angle=0.5*t:ow=512:oh=512',fade=t=out:st=60:d=3",
        "-af", f"afade=in:st=0:d=3,afade=out:st={duration - 3}:d=3",
        "-c:a", "aac", "-b:a", "128k",
        "-fs", "7M",
        "-map", "0:a:0", "-map", "1:v:0",
        output_path
    )
    success, _ = await run_ffmpeg(cmd, dry_run=dry_run)
    return success

async def make_rotating_circle_video_bytes(
    audio_path: str,
    cover_path: str,
    start_time: int = 0,
    duration: int = 60,
    dry_run: bool = False
) -> Optional[bytes]:
    if not check_ffmpeg_installed():
        logging.error("ffmpeg не установлен в системе.")
        return None

    prepared_cover = cover_path
    if not cover_path.lower().endswith("_512.jpg"):
        prepared_cover = cover_path.rsplit('.', 1)[0] + "_512.jpg"
        await prepare_cover(cover_path, prepared_cover, 512)

    cmd = build_ffmpeg_cmd(
        "-y", "-ss", str(start_time), "-t", str(duration),
        "-i", audio_path,
        "-loop", "1", "-i", prepared_cover,
        "-c:v", "libx264",
        "-vf", "scale=512:512,rotate='angle=0.5*t:ow=512:oh=512',format=yuv420p,fade=t=out:st=57:d=3",
        "-af", f"apad=pad_dur={duration},afade=in:st=0:d=3,afade=out:st={duration - 3}:d=3",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-profile:v", "baseline",
        "-level", "3.0",
        "-fs", "7M",
        "-map", "0:a:0", "-map", "1:v:0",
        "-f", "mp4", "pipe:1"
    )
    success, stdout = await run_ffmpeg(cmd, dry_run=dry_run)
    return stdout if success else None
