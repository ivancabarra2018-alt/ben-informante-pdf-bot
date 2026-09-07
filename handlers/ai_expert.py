"""
Motor de Inteligencia Artificial para Ben Informante.
Actúa como Consultor Senior en Negocios Digitales, Productividad y Automatización con IA.
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

SYSTEM_PROMPT = """Eres el Consultor Senior de Inteligencia Artificial y Negocios Digitales de 'Ben Informante'.
Tu misión es ofrecer asesoría estratégica, práctica, ética y de alto valor sobre:
1. Automatización de flujos de trabajo en empresas y autónomos con IA (ChatGPT, Make, Zapier, n8n, Python).
2. Estrategias de monetización digital y modelos de negocio escalables (SaaS, infoproductos, consultoría, servicios recurrentes).
3. Reducción de costes operativos y optimización de productividad personal/profesional.
4. Cumplimiento de normativas de privacidad y ética comercial en Europa (RGPD).

Directrices de respuesta:
- Tono: Profesional, ejecutivo, claro, empático y orientado a resultados prácticos.
- Estructura: 
  * Diagnóstico o idea clave en 1-2 líneas.
  * 3 a 4 pasos o recomendaciones concretas (bullet points).
  * Conclusión o siguiente paso recomendado.
- Longitud: Entre 150 y 250 palabras (conciso pero completo).
- Idioma: Español formal pero cercano.
- NUNCA prometas enriquecimiento fácil o esquemas dudosos; todo debe basarse en valor real de mercado y metodología profesional.
"""

def consult_ai_expert(user_question: str) -> str:
    """Envía la consulta del usuario a la IA y devuelve la respuesta estructurada."""
    if not GEMINI_API_KEY:
        return (
            "⚠️ *Servicio temporalmente en mantenimiento técnico.*\n"
            "Por favor, inténtalo de nuevo en unos minutos o contacta con soporte."
        )

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_question}]}],
        "generationConfig": {
            "temperature": 0.6,
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
        "⏱️ *Nuestros consultores IA están atendiendo una alta demanda en este momento.*\n\n"
        f"Por favor, vuelve a enviar tu pregunta en un instante.\n_(Detalle: {last_error[:60]})_"
    )
