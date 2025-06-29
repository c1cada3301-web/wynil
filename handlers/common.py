from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from handlers.keyboards import (
    main_menu_kb, cut_kb, cover_type_kb, back_kb,
    promo_kb, status_kb, pay_kb, payment_keyboard
)
from handlers.promo import PromoFSM
from db import get_user, set_subscription
from utils import (
    save_audio,
    extract_cover,
    save_cover,
    prepare_cover,
    make_rotating_circle_video_bytes,
    send_result,
    audio_to_ogg,
    is_user_subscribed,
)

import tempfile
import os

router = Router()

CHANNEL_ID = "-1002083327630"  # ID твоего канала @swr24

class AudioFSM(StatesGroup):
    waiting_for_audio = State()
    waiting_for_cut = State()
    waiting_for_cover = State()
    waiting_for_custom_cover = State()

async def show_main_menu(message_or_callback, state: FSMContext):
    await state.clear()
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer("Главное меню:", reply_markup=main_menu_kb)
    elif isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer()
        try:
            await message_or_callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb)
        except Exception:
            await message_or_callback.message.delete()
            await message_or_callback.message.answer("Главное меню:", reply_markup=main_menu_kb)

@router.message(Command("start"))
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext, bot):
    is_subscribed = await is_user_subscribed(bot, message.from_user.id, CHANNEL_ID)
    await set_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        await message.answer("Подпишитесь на канал @swr24, чтобы пользоваться ботом.")
        return
    await message.answer(
        "<b>💞Добро пожаловать в Svinyl!</b>\n\n"
        "🎼С помощью этого бота ты можешь создать свои <b>музыкальные сниппеты</b> в виде кружков телеграм. "
        "Отправь мне mp3-файл с обложкой, настрой под свои нужды и получи результат!\n\n"
        "💥Бот работает <b>бесплатно первые 7 дней</b>, дальше нужно оплачивать <b>подписку за 50 звёзд.</b> "
        "И поверь, это дешевле, чем у конкурентов <b>в 50%!</b>\n\n"
        "❤️Обязательно, <b>подпишись на наш телеграм-канал</b> @swr24, дабы быть в курсе <b>раздачи промокодов</b> на бесплатное пользование. Удачи!",
        reply_markup=main_menu_kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "start")
async def main_menu_start(callback: CallbackQuery, state: FSMContext, bot):
    is_subscribed = await is_user_subscribed(bot, callback.from_user.id, CHANNEL_ID)
    await set_subscription(callback.from_user.id, is_subscribed)
    if not is_subscribed:
        await callback.message.answer("Подпишитесь на канал @swr24, чтобы пользоваться ботом.")
        return
    await show_main_menu(callback, state)

@router.callback_query(F.data == "create_circle")
async def start_create_circle(callback: CallbackQuery, state: FSMContext, bot):
    is_subscribed = await is_user_subscribed(bot, callback.from_user.id, CHANNEL_ID)
    await set_subscription(callback.from_user.id, is_subscribed)
    if not is_subscribed:
        await callback.message.answer("Подпишитесь на канал @swr24, чтобы продолжить.")
        return
    await callback.answer()
    try:
        await callback.message.edit_text("Пришлите mp3-файл с обложкой.")
    except Exception:
        await callback.message.delete()
        await callback.message.answer("Пришлите mp3-файл с обложкой.")
    await state.set_state(AudioFSM.waiting_for_audio)

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb)
    except Exception:
        await callback.message.delete()
        await callback.message.answer("Главное меню:", reply_markup=main_menu_kb)
    await state.clear()

@router.callback_query(F.data == "promo")
async def main_menu_promo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введите промокод одним сообщением.", reply_markup=promo_kb)
    await state.set_state(PromoFSM.waiting_for_code)

@router.callback_query(F.data == "pay")
async def main_menu_pay(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "Для оплаты используйте Telegram Stars (звёзды). Нажмите кнопку ниже для оплаты.",
        reply_markup=pay_kb
    )

@router.callback_query(F.data == "status")
async def main_menu_status(callback: CallbackQuery):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Пользователь не найден.", reply_markup=status_kb)
    else:
        is_subscribed, free_until, has_unlimited = user[2], user[3], user[4]
        if has_unlimited:
            status = "Бессрочный доступ"
            duration = "∞"
        elif is_subscribed:
            status = "Подписка активна"
            duration = f"до {free_until}"
        elif free_until:
            status = "Бесплатный период"
            duration = f"до {free_until}"
        else:
            status = "Нет доступа"
            duration = "-"
        await callback.message.answer(
            f"Ваш статус: {status}\nДлительность подписки: {duration}",
            reply_markup=status_kb
        )

@router.callback_query(F.data == "pay_stars")
async def handle_pay_stars(callback: CallbackQuery):
    await callback.answer()
    prices = [LabeledPrice(label="XTR", amount=50)]
    await callback.message.answer_invoice(
        title="Оформление подписки",
        description="Оплатить бота за 50 звёзд!",
        provider_token="1877036958:TEST:f28652a4dc644148075ca5df733d2c055f6d18b4",  # <-- Укажите ваш provider_token для Telegram Stars
        currency="XTR",
        prices=prices,
        payload="channel_support",
        reply_markup=payment_keyboard(),
    )

@router.message(AudioFSM.waiting_for_custom_cover, F.photo)
async def handle_photo_cover(message: Message, state: FSMContext):
    await message.delete()
    cover_path = await save_cover(message)
    await state.update_data(final_cover=cover_path)
    processing_msg = await message.answer("⏳ Трек обрабатывается, пожалуйста, подождите...")
    await send_result(message, state)
    await processing_msg.delete()

@router.callback_query(AudioFSM.waiting_for_cover, F.data.in_(["cover_file", "cover_default"]))
async def handle_cover_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    if callback.data == "cover_default":
        cover_path = "default_cover.jpg"
    else:
        cover_path = data.get("cover_path", "default_cover.jpg")
    prepared_cover = cover_path.rsplit('.', 1)[0] + "_512.jpg"
    await prepare_cover(cover_path, prepared_cover, 512)
    await state.update_data(final_cover=prepared_cover)
    processing_msg = await callback.message.answer("⏳ Трек обрабатывается, пожалуйста, подождите...")
    await send_result(callback.message, state)
    await processing_msg.delete()

@router.message(AudioFSM.waiting_for_audio, (F.document & (F.document.mime_type == "audio/mpeg")) | F.audio)
async def handle_mp3(message: Message, state: FSMContext):
    processing_msg = await message.answer("⏳ Трек обрабатывается, пожалуйста, подождите...")
    mp3_path = await save_audio(message)  # Используем только функцию из utils.py
    cover_path = await extract_cover(mp3_path)
    await state.update_data(mp3_path=mp3_path, cover_path=cover_path)
    await processing_msg.delete()
    await message.answer("Файл получен, выберите точку обрезки:", reply_markup=cut_kb)
    await state.set_state(AudioFSM.waiting_for_cut)

keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Обложка из файла", callback_data="cover_file"),
        InlineKeyboardButton(text="Стандартная обложка", callback_data="cover_default"),
        InlineKeyboardButton(text="Своя обложка", callback_data="cover_custom"),
    ],
    [
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")
    ]
])
