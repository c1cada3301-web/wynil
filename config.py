import os

# Токен бота
API_TOKEN = "7929920502:AAHiDnjAjZPJWUqFMmeegMBxkZFk6aYYYZE"

# ID канала, на который нужно подписаться
REQUIRED_CHANNEL = "-1002083327630"

# Временная директория
TEMP_DIR = "temp"

# Директория для статических файлов
ASSETS_DIR = "assets"

# Обложка по умолчанию
DEFAULT_COVER = os.path.join(ASSETS_DIR, "default_cover.jpg")

# Добавьте проверку обязательных параметров
if not API_TOKEN:
    raise ValueError("API_TOKEN не задан! Завершение работы.")

# Создаем необходимые директории
os.makedirs(TEMP_DIR, exist_ok=True)
print(f"Временная директория: {TEMP_DIR} (существует)")

os.makedirs(ASSETS_DIR, exist_ok=True)
print(f"Директория для ресурсов: {ASSETS_DIR} (существует)")

# Проверяем наличие обложки по умолчанию
if not os.path.exists(DEFAULT_COVER):
    print(f"⚠️ Внимание: Обложка по умолчанию не найдена по пути {DEFAULT_COVER}")
    print("Пожалуйста, загрузите файл default_cover.jpg в папку assets/")