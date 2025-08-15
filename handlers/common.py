from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from handlers.keyboards import main_menu_kb, back_kb
from db import get_user, set_subscription, check_access
from utils import is_user_subscribed
import logging

router = Router()
logger = logging.getLogger(__name__)

CHANNEL_ID = "-1002083327630"  # ID вашего канала @swr24
WELCOME_TEXT = (
    "🌈 <b>Привет! Я помогу тебе создать стильный видеокружок</b>\n\n"
    "✨ Просто нажми <b>«Создать кружок»</b> и загрузи свой трек\n\n"
    "💖 <b>Бот абсолютно бесплатный</b>, буду рад вашей поддержке сервера\n\n"
    "🎛️ Проект лейбла <b>Sovietwave Records</b> — @swr24"
)

async def check_subscription_and_send_welcome(message: Message):
    """Проверяет подписку и отправляет приветственное сообщение"""
    try:
        # Проверяем подписку на канал
        is_sub = await is_user_subscribed(message.bot, message.from_user.id, CHANNEL_ID)
        await set_subscription(message.from_user.id, is_sub)
        
        if not is_sub:
            await message.answer(
                "❌ Для использования бота необходимо подписаться на канал @swr24.\n\n"
                "Пожалуйста, подпишитесь и нажмите /start снова.",
                parse_mode="HTML"
            )
            return False
        
        # Если подписка есть - показываем приветственное сообщение
        await message.answer(
            WELCOME_TEXT,
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при запуске бота. Пожалуйста, попробуйте позже.",
            reply_markup=main_menu_kb()
        )
        return False

@router.message(Command("start"))
@router.message(F.text == "/start")
async def send_welcome(message: Message):
    await check_subscription_and_send_welcome(message)

async def show_main_menu(message_or_callback, state: FSMContext):
    """Показывает главное меню с очисткой состояния"""
    await state.clear()
    try:
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer("Главное меню:", reply_markup=main_menu_kb())
        elif isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer()
            await message_or_callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    except Exception:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.delete()
            await message_or_callback.message.answer("Главное меню:", reply_markup=main_menu_kb())

@router.callback_query(F.data == "start")
async def main_menu_start(callback: CallbackQuery, state: FSMContext):
    is_subscribed = await is_user_subscribed(callback.bot, callback.from_user.id, CHANNEL_ID)
    await set_subscription(callback.from_user.id, is_subscribed)
    
    if not is_subscribed:
        await callback.message.answer("❌ Для использования бота необходимо подписаться на канал @swr24.")
        return
    
    await callback.message.edit_text(
        "🌈 Привет! Я помогу тебе создать стильный видеокружок.\n\n"
        "✨ Просто нажми «Создать кружок» и загрузи свой трек\n"
        "🔥 Проект лейбла Sovietwave Records @swr24",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_main_menu(callback, state)

@router.message(F.text == "🎵 Создать кружок")
async def create_circle_handler(message: Message, state: FSMContext):
    if not await check_access(message.from_user.id):
        await message.answer("❌ Для использования бота необходимо подписаться на канал @swr24.")
        return
    
    await message.answer(
        "⬇️ Загрузи видео или аудио файл:",
        reply_markup=back_kb()
    )

@router.message(F.text == "❤️ Поддержать проект")
async def support_handler(message: Message):
    await message.answer(
        "💖 Поддержи развитие проекта:\n\n"
        "👉 https://t.me/tribute/app?startapp=dswf\n\n"
        "Каждый донат помогает улучшать бота!",
        reply_markup=back_kb(),
        disable_web_page_preview=True
    )

@router.message(F.text == "⬅️ Назад")
async def back_handler(message: Message, state: FSMContext):
    await show_main_menu(message, state)