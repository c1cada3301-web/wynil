from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    # Основные кнопки
    builder.row(
        InlineKeyboardButton(text="✨ Создать кружок", callback_data="create_circle")
    )
    builder.row(
        InlineKeyboardButton(text="❤️ Поддержать проект", url="https://t.me/tribute/app?startapp=dswf")
    )
    return builder.as_markup()

def cut_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="00:00", callback_data="cut_0"),
        InlineKeyboardButton(text="00:30", callback_data="cut_30"),
        InlineKeyboardButton(text="01:00", callback_data="cut_60"),
    )
    builder.row(
        InlineKeyboardButton(text="01:30", callback_data="cut_90"),
        InlineKeyboardButton(text="02:00", callback_data="cut_120"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    return builder.as_markup()

def cover_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📁 Из файла/метаданных", callback_data="cover_file"),
    )
    builder.row(
        InlineKeyboardButton(text="🖼 Загрузить свою", callback_data="cover_custom"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Стандартная", callback_data="cover_default"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    return builder.as_markup()

def back_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    return builder.as_markup()