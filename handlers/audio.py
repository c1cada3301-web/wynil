import asyncio
import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from .keyboards import cut_kb, cover_type_kb, main_menu_kb
from config import DEFAULT_COVER
from utils import save_audio, save_cover, extract_cover, make_video_async, get_track_metadata, send_result, prepare_cover

logging.basicConfig(level=logging.INFO)
logging.getLogger("aiogram.event").setLevel(logging.DEBUG)

router = Router()

class AudioFSM(StatesGroup):
    waiting_for_audio = State()
    waiting_for_cut = State()
    waiting_for_cover = State()
    waiting_for_custom_cover = State()

@router.callback_query(F.data == "create_circle")
async def start_audio(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("Пришлите mp3-файл с обложкой.")
    await state.set_state(AudioFSM.waiting_for_audio)

@router.message(AudioFSM.waiting_for_audio, (F.document & (F.document.mime_type == "audio/mpeg")) | F.audio)
async def handle_mp3(message: Message, state: FSMContext):
    processing_msg = await message.answer("⏳ Трек обрабатывается, пожалуйста, подождите...")
    mp3_path = await save_audio(message)  # Только вызов функции из utils.py
    cover_path = await extract_cover(mp3_path)
    await state.update_data(mp3_path=mp3_path, cover_path=cover_path)
    await processing_msg.delete()
    await message.answer("Файл получен, выберите точку обрезки:", reply_markup=cut_kb)
    await state.set_state(AudioFSM.waiting_for_cut)

@router.callback_query(AudioFSM.waiting_for_cut, F.data.startswith("cut_"))
async def handle_cut(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    cut_sec = int(callback.data.split("_")[1])
    await state.update_data(cut_sec=cut_sec)
    # Отправляем меню выбора обложки
    msg = await callback.message.answer("Выберите тип обложки:", reply_markup=cover_type_kb)
    # Сохраняем id сообщения с меню выбора обложки, чтобы потом удалить
    await state.update_data(cover_menu_msg_id=msg.message_id)
    await state.set_state(AudioFSM.waiting_for_cover)

@router.callback_query(AudioFSM.waiting_for_cover, F.data == "cover_custom")
async def handle_custom_cover(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    # Удаляем меню выбора обложки
    await callback.message.delete()
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    await callback.message.answer("Пришлите свою обложку (jpg/png).", reply_markup=back_kb)
    await state.set_state(AudioFSM.waiting_for_custom_cover)

@router.message(AudioFSM.waiting_for_custom_cover, F.photo)
async def handle_photo_cover(message: Message, state: FSMContext):
    # Удаляем меню выбора обложки, если оно осталось
    data = await state.get_data()
    cover_menu_msg_id = data.get("cover_menu_msg_id")
    if cover_menu_msg_id:
        try:
            await message.bot.delete_message(message.chat.id, cover_menu_msg_id)
        except Exception:
            pass
    await message.delete()
    cover_path = await save_cover(message)
    await state.update_data(final_cover=cover_path)
    processing_msg = await message.answer("⏳ Трек обрабатывается, пожалуйста, подождите...")
    await send_result(message, state)
    await processing_msg.delete()

@router.callback_query(AudioFSM.waiting_for_cover, F.data.in_(["cover_file", "cover_default"]))
async def handle_cover_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    data = await state.get_data()
    if callback.data == "cover_default":
        cover_path = "default_cover.jpg"
    else:
        cover_path = data.get("cover_path") or "default_cover.jpg"
    prepared_cover = cover_path.rsplit('.', 1)[0] + "_512.jpg"
    await prepare_cover(cover_path, prepared_cover, 512)
    await state.update_data(final_cover=prepared_cover)
    processing_msg = await callback.message.answer("⏳ Трек обрабатывается, пожалуйста, подождите...")
    await send_result(callback.message, state)
    await processing_msg.delete()