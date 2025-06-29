from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from handlers.keyboards import main_menu_kb

router = Router()

class PromoFSM:
    waiting_for_code = "waiting_for_code"

@router.callback_query(F.data == "promo")
async def main_menu_promo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("Введите промокод одним сообщением.")
    await state.set_state(PromoFSM.waiting_for_code)

@router.message(F.text, F.state == PromoFSM.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext):
    code = message.text.strip()
    # Здесь ваша логика проверки промокода
    await message.answer("Промокод обработан.", reply_markup=main_menu_kb)
    await state.clear()