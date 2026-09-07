"""
Motor de Inteligencia Artificial para Accede Gratis Tipster VIP.
Especializado en Detección de Value Bets (+EV), Gestión de Stake y Análisis de Cuotas.
"""
import logging
import requests
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-pro-latest",
]
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """Eres el Analista Cuantitativo y Especialista en Pronósticos con Inteligencia Artificial del canal VIP de 'Accede Gratis'.
Tu labor es proporcionar análisis riguroso, matemático y estadístico para ayudar a los apostadores a tomar decisiones informadas con base en el concepto de Valor Esperado (+EV) y gestión responsable del capital.

Al analizar un evento deportivo (fútbol, baloncesto, tenis, etc.):
1. Resumen Táctico / Momento de Forma: Contexto de bajas clave, dinámicas y estilo de juego (1-2 líneas).
2. Datos Clave y Modelos Estadísticos: Factores que el mercado de cuotas está pasando por alto (xG, rendimiento local/visitante, tendencias históricas).
3. Veredicto de Valor (+EV): Indica qué mercado o selección ofrece una probabilidad matemática superior a la cuota ofrecida.
4. Gestión de Riesgo (Stake Sugerido): Recomienda siempre un stake prudente (Stake 1/10 o Stake 2/10 máximo, equivalente al 1% o 2% del bankroll).

Directrices de estilo:
- Tono: Profesional, seguro, analítico y directo al grano.
- Longitud: Entre 150 y 230 palabras (fácil de leer en móvil).
- Idioma: Español.
- Finaliza siempre con un recordatorio de responsabilidad: "📊 Recuerda seguir siempre una estricta gestión de bankroll."
"""

def consult_tipster_ai(user_question: str) -> str:
    """Envía la consulta deportiva al motor IA y devuelve el análisis de valor."""
    if not GEMINI_API_KEY:
        return (
            "⚠️ *Servicio temporalmente en optimización de servidores.*\n"
            "Por favor, inténtalo de nuevo en unos instantes."
        )

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_question}]}],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 600,
        }
    }

    last_error = ""
    for model in GEMINI_MODELS:
        try:
            url = f"{BASE_URL.format(model=model)}?key={GEMINI_API_KEY}"
            resp = requests.post(url, json=payload, timeout=20)
            data = resp.json()

            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()

            err = data.get("error", {}).get("message", "")
            last_error = err
            logger.warning(f"Modelo {model} devolvió error: {err}")
        except requests.Timeout:
            last_error = "Tiempo de espera agotado"
            logger.warning(f"Timeout en modelo {model}")
        except Exception as e:
            last_error = str(e)
            logger.error(f"Excepción en {model}: {e}")

    return (
        "⏱️ *Nuestros algoritmos analíticos están procesando un alto volumen de partidos.*\n\n"
        f"Por favor, vuelve a enviar tu consulta en unos segundos.\n_(Detalle: {last_error[:60]})_"
    )
