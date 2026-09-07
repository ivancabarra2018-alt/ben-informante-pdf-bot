"""
Configuración oficial de Accede Gratis (@Accedogratis_bot)
Embudo de Conversión VIP para Tipster con Inteligencia Artificial.
Cumplimiento normativo para Telegram Ads (Unión Europea).
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8723584690:AAEtB61YXNKD67rwNNlUW_NyDpFkNk0txak")
BOT_USERNAME = "Accedogratis_bot"
BOT_NAME = "Accede Gratis | Pronósticos & IA VIP"

# API Key de IA (Google Gemini) - inyectada por variable de entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Enlace de pago oficial para el acceso VIP
PAYMENT_URL = os.getenv("PAYMENT_URL", "https://store.kunfupay.com/elprograma/pgUKnc9F")

# Soporte
SUPPORT_USER = "@AccesoSoporteVIP"
SUPPORT_URL = "https://t.me/Accedogratis_bot"

# Límites de la versión gratuita
FREE_ANALYSIS_LIMIT = 2

# Precio oficial en Euros
PRICE_EUR = "Solo 1.99€ al mes"

# Base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "tipster_funnel.db")
