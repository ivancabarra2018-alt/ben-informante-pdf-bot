"""
Configuración central del bot PDF Ben Informante (@Accedogratis_bot)
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN   = os.getenv("BOT_TOKEN", "8723584690:AAEtB61YXNKD67rwNNlUW_NyDpFkNk0txak")
BOT_USERNAME = "Accedogratis_bot"
BOT_NAME     = "Ben Informante"
DB_PATH      = os.path.join(os.path.dirname(__file__), "data", "pdf_bot.db")
TEMP_DIR     = os.path.join(os.path.dirname(__file__), "temp")
ADMIN_IDS: list[int] = []   # Añade tu Telegram ID aquí

MAX_FILE_MB   = 20     # Máximo tamaño PDF a procesar
MAX_MERGE_FILES = 10   # Máximo PDFs a unir de una vez
