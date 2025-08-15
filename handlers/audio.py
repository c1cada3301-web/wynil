import logging
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from .keyboards import cut_kb, cover_type_kb
from config import DEFAULT_COVER
from utils import (
    save_audio, 
    save_cover, 
    extract_cover, 
    send_result, 
    convert_to_square,
    cut_audio_async
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

class AudioFSM(StatesGroup):
    waiting_for_audio = State()
    waiting_for_cut = State()
    waiting_for_cover = State()
    waiting_for_custom_cover = State()

async def delete_previous_messages(bot, chat_id, state):
    """Удаляет все предыдущие сообщения бота в этом состоянии"""
    data = await state.get_data()
    message_ids = data.get("message_ids", [])
    
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except TelegramBadRequest as e:
            if "message to delete not found" not in str(e):
                logger.warning(f"Ошибка удаления сообщения {msg_id}: {e}")
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение {msg_id}: {e}")
    
    await state.update_data(message_ids=[])

async def save_and_track_message(message, state):
    """Сохраняет сообщение для последующего удаления"""
    data = await state.get_data()
    message_ids = data.get("message_ids", [])
    message_ids.append(message.message_id)
    await state.update_data(message_ids=message_ids)
    return message

@router.callback_query(F.data == "create_circle")
async def start_audio(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        
        try:
            await callback.message.delete()
        except TelegramBadRequest as e:
            if "message to delete not found" not in str(e):
                logger.warning(f"Ошибка удаления сообщения: {e}")
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        
        msg = await callback.message.answer("🎵 Пришлите mp3 или m4a файл с обложкой или аудио сообщение.")
        await save_and_track_message(msg, state)
        await state.set_state(AudioFSM.waiting_for_audio)
    except Exception as e:
        logger.error(f"Ошибка в start_audio: {e}")
        await callback.message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте ещё раз.")

@router.message(
    AudioFSM.waiting_for_audio, 
    (F.document & (F.document.mime_type.in_(["audio/mpeg", "audio/mp4", "audio/x-m4a"]))) | F.audio
)
async def handle_audio(message: Message, state: FSMContext):
    try:
        await delete_previous_messages(message.bot, message.chat.id, state)
        
        processing_msg = await message.answer("⏳ Обработка трека...")
        await save_and_track_message(processing_msg, state)
        
        mp3_path = await save_audio(message)
        
        track_info = "🎵 Ваш трек"
        if message.audio:
            artist = message.audio.performer or ""
            title = message.audio.title or ""
            if artist or title:
                track_info = f"🎶 {artist} - {title}"
        elif message.document:
            # Для документов попробуем получить имя файла
            if message.document.file_name:
                track_info = f"🎵 {message.document.file_name}"
        
        await state.update_data(
            audio_path=mp3_path,
            track_info=track_info
        )
        
        msg = await processing_msg.edit_text(
            f"{track_info}\n\nВыберите точку обрезки:",
            reply_markup=cut_kb()
        )
        await save_and_track_message(msg, state)
        await state.set_state(AudioFSM.waiting_for_cut)
    except Exception as e:
        logger.error(f"Ошибка обработки аудио: {e}")
        await delete_previous_messages(message.bot, message.chat.id, state)
        await message.answer("❌ Ошибка обработки файла. Попробуйте другой файл.")
        await state.clear()

@router.callback_query(AudioFSM.waiting_for_cut, F.data.startswith("cut_"))
async def handle_cut(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await delete_previous_messages(callback.bot, callback.message.chat.id, state)
        
        data = await state.get_data()
        start_sec = int(callback.data.split("_")[1])
        
        processing_msg = await callback.message.answer("✂️ Обрезаю аудио...")
        await save_and_track_message(processing_msg, state)
        
        cut_mp3_path = await cut_audio_async(data['audio_path'], start_sec)
        
        cover_msg = await processing_msg.edit_text("🖼️ Извлекаю обложку...")
        cover_path = await extract_cover(cut_mp3_path)
        
        # Обработка случая, когда обложка не найдена
        if not cover_path:
            await cover_msg.edit_text("⚠️ Обложка не найдена в файле. Будет предложен выбор обложки.")
            cover_path = None
        
        await state.update_data(
            audio_path=cut_mp3_path,
            cover_path=cover_path,
            start_time=0,
            cut_sec=start_sec
        )
        
        cover_menu = await cover_msg.edit_text(
            "Выберите тип обложки:",
            reply_markup=cover_type_kb()
        )
        await save_and_track_message(cover_menu, state)
        await state.set_state(AudioFSM.waiting_for_cover)
    except Exception as e:
        logger.error(f"Ошибка в handle_cut: {e}")
        await delete_previous_messages(callback.bot, callback.message.chat.id, state)
        await callback.message.answer("❌ Ошибка обработки. Пожалуйста, попробуйте ещё раз.")
        await state.clear()

@router.callback_query(AudioFSM.waiting_for_custom_cover, F.data == "back_to_cover_menu")
async def back_to_cover_menu(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        cover_menu = await callback.message.answer(
            "Выберите тип обложки:",
            reply_markup=cover_type_kb()
        )
        await save_and_track_message(cover_menu, state)
        await state.set_state(AudioFSM.waiting_for_cover)
    except Exception as e:
        logger.error(f"Ошибка в back_to_cover_menu: {e}")
        await callback.message.answer("❌ Ошибка. Пожалуйста, попробуйте ещё раз.")

@router.callback_query(AudioFSM.waiting_for_cover, F.data == "cover_custom")
async def handle_custom_cover(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info("Обработка выбора: Загрузить свою обложку")
        await callback.answer()
        
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_cover_menu")]
        ])
        
        msg = await callback.message.answer(
            "🖼️ Пришлите свою обложку (изображение):",
            reply_markup=back_kb
        )
        await save_and_track_message(msg, state)
        await state.set_state(AudioFSM.waiting_for_custom_cover)
    except Exception as e:
        logger.error(f"Ошибка в handle_custom_cover: {e}")
        await callback.message.answer("❌ Ошибка. Пожалуйста, попробуйте ещё раз.")

@router.callback_query(AudioFSM.waiting_for_cover, F.data == "cover_default")
async def handle_default_cover(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info("Обработка выбора: Стандартная обложка")
        await callback.answer()
        await state.update_data(cover_path=DEFAULT_COVER)
        await start_video_processing(callback.message, state)
    except Exception as e:
        logger.error(f"Ошибка в handle_default_cover: {e}")
        await callback.message.answer("❌ Ошибка. Пожалуйста, попробуйте ещё раз.")

@router.callback_query(AudioFSM.waiting_for_cover, F.data == "cover_file")
async def handle_file_cover(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info("Обработка выбора: Обложка из файла/метаданных")
        await callback.answer()
        await start_video_processing(callback.message, state)
    except Exception as e:
        logger.error(f"Ошибка в handle_file_cover: {e}")
        await callback.message.answer("❌ Ошибка. Пожалуйста, попробуйте ещё раз.")

@router.message(AudioFSM.waiting_for_custom_cover, F.photo)
async def handle_photo_cover(message: Message, state: FSMContext):
    try:
        await delete_previous_messages(message.bot, message.chat.id, state)
        
        processing_msg = await message.answer("⏳ Загружаю обложку...")
        await save_and_track_message(processing_msg, state)
        
        cover_path = await save_cover(message)
        square_cover = await convert_to_square(cover_path)
        
        await state.update_data(cover_path=square_cover)
        await start_video_processing(message, state)
    except Exception as e:
        logger.error(f"Ошибка обработки обложки: {e}")
        await delete_previous_messages(message.bot, message.chat.id, state)
        error_msg = await message.answer("❌ Ошибка обработки изображения. Попробуйте другое.")
        await save_and_track_message(error_msg, state)

async def start_video_processing(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        track_info = data.get('track_info', 'Ваш трек')
        
        processing_msg = await message.answer(
            f"⏳ Генерирую видеокружок для:\n{track_info}\n\nЭто займет 20-60 секунд..."
        )
        await save_and_track_message(processing_msg, state)
        
        await send_result(message, state)
    except Exception as e:
        logger.error(f"Ошибка генерации видео: {e}")
        await message.answer("❌ Ошибка генерации видео. Попробуйте другой трек.")
    finally:
        await delete_previous_messages(message.bot, message.chat.id, state)
        await state.clear()