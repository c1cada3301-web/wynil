from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

main_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🎵 Начать", callback_data="create_circle"),
        InlineKeyboardButton(text="🏷 Промокод", callback_data="promo"),
    ],
    [
        InlineKeyboardButton(text="💳 Оплата", callback_data="pay"),
        InlineKeyboardButton(text="ℹ️ Мой статус", callback_data="status"),
    ]
])

cut_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="00:00", callback_data="cut_0"),
        InlineKeyboardButton(text="00:30", callback_data="cut_30"),
        InlineKeyboardButton(text="01:00", callback_data="cut_60"),
        InlineKeyboardButton(text="01:30", callback_data="cut_90"),
        InlineKeyboardButton(text="02:00", callback_data="cut_120"),
    ],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
])

cover_type_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Обложка из файла", callback_data="cover_file"),
        InlineKeyboardButton(text="Стандартная обложка", callback_data="cover_default"),
        InlineKeyboardButton(text="Своя обложка", callback_data="cover_custom"),
    ],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
])

back_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
])

# Новые клавиатуры:
promo_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
])

status_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
])

pay_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💫 Оплатить звёздами Telegram", callback_data="pay_stars")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
])

def payment_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Оплатить 50 ⭐️", pay=True)
    return builder.as_markup()