"""
Configuración oficial de Accede Gratis Tipster VIP (@Accedogratis_bot)
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8723584690:AAEtB61YXNKD67rwNNlUW_NyDpFkNk0txak")
BOT_USERNAME = "Accedogratis_bot"
BOT_NAME = "Accede Gratis | Pronósticos & IA VIP"

# API Key de IA (Google Gemini) - inyectada por variable de entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

DEFAULT_PAYMENT_URL = os.getenv("PAYMENT_URL", "https://store.kunfupay.com/elprograma/pgUKnc9F")
PAYMENT_URL = DEFAULT_PAYMENT_URL

# Precio oficial
PRICE_EUR = "Solo 1.99€ al mes"

# Soporte
SUPPORT_USER = "@AccesoSoporteVIP"
SUPPORT_URL = "https://t.me/Accedogratis_bot"

# Base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "tipster_pro.db")
