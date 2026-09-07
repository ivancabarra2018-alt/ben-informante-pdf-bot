"""
Configuración oficial de Ben Informante - Academia de Negocios Digitales & IA
Cumplimiento normativo para Telegram Ads (Unión Europea).
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8723584690:AAEtB61YXNKD67rwNNlUW_NyDpFkNk0txak")
BOT_USERNAME = "Accedogratis_bot"
BOT_NAME = "Ben Informante | Negocios & IA"

# API Key de IA (Google Gemini) - se inyecta por variable de entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# Enlace de pago oficial para la membresía PRO (editable en cualquier momento)
PAYMENT_URL = os.getenv("PAYMENT_URL", "https://t.me/Accedogratis_bot?start=membresia_pro")

# Enlace o contacto de soporte
SUPPORT_USER = "@BenInformanteSoporte"
SUPPORT_URL = "https://t.me/Accedogratis_bot"

# Canal oficial / comunidad
OFFICIAL_CHANNEL = "https://t.me/Accedogratis_bot"

# Límites de la versión gratuita
FREE_QUESTIONS_LIMIT = 2

# Precio oficial en Euros para transparencia y cumplimiento de Telegram Ads
PRICE_EUR = "19.99€/mes"

# Base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "business_academy.db")
