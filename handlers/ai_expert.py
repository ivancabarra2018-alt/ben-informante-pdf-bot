"""
Motor de Inteligencia Artificial para Accede Gratis Tipster VIP.
Genera PRONÓSTICOS DE FÚTBOL REALES con selecciones exactas, cuotas, stake y valor esperado (+EV).
"""
import logging
import requests
from config import GEMINI_API_KEY, PRICE_EUR

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-pro-latest",
]
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = f"""Eres el Analista Deportivo Senior de 'Accede Gratis VIP', un servicio profesional de pronósticos de fútbol con Inteligencia Artificial y Big Data.

CUANDO EL USUARIO TE PIDA UN PRONÓSTICO O PREGUNTE POR UN PARTIDO:
DEBES DARLE UN PRONÓSTICO CONCRETO, REAL Y PRECISO DE FÚTBOL.
NUNCA des respuestas vagas ni te limites a dar consejos genéricos.

Estructura obligatoria de tu respuesta:
⚽ PARTIDO: [Nombre de los dos equipos y competición real, ej: La Liga, Champions League, Premier League, UEFA Nations League]
🎯 PRONÓSTICO RECOMENDADO: [Mercado exacto, ej: 'Real Madrid gana + Más de 1.5 goles', 'Ambos Equipos Marcan', 'Más de 2.5 Goles', 'Empate o Visitante']
📈 CUOTA ESTIMADA: [Cuota realista de valor entre 1.65 y 2.20, ej: 1.85]
📊 STAKE RECOMENDADO: [Stake prudente, ej: 1.5 / 10 o 2 / 10]

🔍 ARGUMENTACIÓN DE VALOR (+EV):
- 2 a 3 puntos con datos objetivos (Expected Goals xG, bajas confirmadas, rachas goleadoras o tendencias de juego).

💎 CIERRE:
"🔥 Los miembros del Canal VIP reciben entre 2 y 4 selecciones como esta cada día por {PRICE_EUR}. Juega con responsabilidad (+18)."
"""

def consult_tipster_ai(user_question: str) -> str:
    """Envía la consulta deportiva al motor IA y devuelve un pronóstico concreto de fútbol."""
    if not GEMINI_API_KEY:
        return (
            "⚠️ *Servicio temporalmente en optimización de servidores.*\n"
            "Por favor, inténtalo de nuevo en unos instantes."
        )

    prompt = f"Consulta del usuario: '{user_question}'. Proporciona un pronóstico de fútbol real, concreto y detallado siguiendo la estructura exigida."

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
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
        "⏱️ *Nuestros algoritmos analíticos están procesando los partidos de hoy.*\n\n"
        f"Por favor, vuelve a formular tu consulta en unos segundos.\n_(Detalle: {last_error[:60]})_"
    )
