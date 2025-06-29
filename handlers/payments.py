from aiogram import Router, F
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery, SuccessfulPayment, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import API_TOKEN, PAYMENT_PROVIDER_TOKEN  # PAYMENT_PROVIDER_TOKEN должен быть задан в config.py
from db import set_subscription, add_user
import datetime

router = Router()

# Настройки подписки
SUBSCRIPTION_PRICE = 50  # Цена подписки
CURRENCY = "XTR"         # Валюта Telegram Stars

@router.message(Command("pay"))
async def pay_command(message: Message):
    await add_user(message.from_user.id, message.from_user.username or "")
    prices = [LabeledPrice(label="Подписка на месяц — 50 звёзд", amount=SUBSCRIPTION_PRICE)]
    await message.answer_invoice(
        title="Оформление подписки",
        description="Подписка на сервис на 30 дней.",
        payload="subscription-stars",
        provider_token=PAYMENT_PROVIDER_TOKEN,  # Укажите ваш токен провайдера
        currency=CURRENCY,
        prices=prices,
        need_name=False,
        need_email=False,
        need_phone_number=False,
        need_shipping_address=False,
        is_flexible=False
    )

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    # Подтверждение готовности к оплате
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    # Устанавливаем подписку пользователю (например, на 30 дней)
    await set_subscription(message.from_user.id, True)
    await message.answer(
        "<b>Спасибо!</b> Ваша подписка активирована. Доступ открыт на 30 дней.",
        parse_mode="HTML"
    )