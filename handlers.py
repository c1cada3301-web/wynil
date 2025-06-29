from aiogram import Router, F
from aiogram.types import Message
from handlers.keyboards import main_menu_kb
from config import REQUIRED_CHANNEL
from utils import is_user_subscribed
from db import set_subscription

WELCOME_TEXT = (
    "👋 Добро пожаловать!\n\n"
    "🎵 Этот бот поможет вам создать кружок из вашего аудиофайла с обложкой, который вы можете кастомизировать под себя.\n\n"
    "🆓 Вам доступен 7-дневный бесплатный доступ ко всему функционалу бота, а также мы раздаём ограниченные промокоды — следите за новостями в группе!\n\n"
    "💫 Наши цены наполовину ниже конкурентов — всего 50 звёзд за полный доступ.\n\n"
    "👇 Выберите действие в главном меню ниже."
)

router = Router()

@router.message(F.text == "/start")
async def send_welcome(message: Message):
    is_sub = await is_user_subscribed(message.bot, message.from_user.id, REQUIRED_CHANNEL)
    await set_subscription(message.from_user.id, is_sub)
    if not is_sub:
        await message.answer("❗ Для использования бота подпишитесь на канал и попробуйте снова.")
        return
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb)