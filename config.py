import os
import dotenv

loaded = dotenv.load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL")
TEMP_DIR = os.getenv("TEMP_DIR", "temp")
ASSETS_DIR = os.getenv("ASSETS_DIR", "assets")
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
