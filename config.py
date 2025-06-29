import os
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = "7929920502:AAHiDnjAjZPJWUqFMmeegMBxkZFk6aYYYZE"
BOT_TOKEN = API_TOKEN
PAYMENT_PROVIDER_TOKEN = os.getenv("1877036958:TEST:f28652a4dc644148075ca5df733d2c055f6d18b4")
REQUIRED_CHANNEL = "-1002083327630"

TEMP_DIR = "temp"  # ← добавьте эту строку!
DEFAULT_COVER = os.path.join(TEMP_DIR, "default_cover.jpg")