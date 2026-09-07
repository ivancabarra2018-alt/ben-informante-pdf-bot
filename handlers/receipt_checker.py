"""
Verificador de Justificantes de Pago con Inteligencia Artificial (Gemini Vision).
Analiza capturas de pantalla, transferencias y comprobantes de Bizum/KunfuPay.
"""
import base64
import logging
import requests
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

GEMINI_VISION_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

def verify_receipt_with_ai(image_bytes: bytes) -> str:
    """Envía la imagen a Gemini Vision para evaluar la legitimidad del comprobante."""
    if not GEMINI_API_KEY:
        return "ℹ️ Justificante recibido (Verificación manual requerida)."

    try:
        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_data
                        }
                    },
                    {
                        "text": (
                            "Eres un auditor de seguridad financiera. Analiza esta captura de pantalla o foto. "
                            "¿Es un justificante o comprobante de pago bancario / pasarela legítimo (Bizum, KunfuPay, Stripe, PayPal, Transferencia)?\n"
                            "Resume en 2 líneas:\n"
                            "1. Veredicto: [Comprobante Válido / No parece pago / Ilegible]\n"
                            "2. Datos detectados: [Importe, fecha o pasarela visible]"
                        )
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 120
            }
        }

        resp = requests.post(f"{GEMINI_VISION_URL}?key={GEMINI_API_KEY}", json=payload, timeout=20)
        data = resp.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text
        err = data.get("error", {}).get("message", "Error de lectura")
        logger.warning(f"Error en Gemini Vision: {err}")
        return f"⚠️ No se pudo procesar automáticamente: {err[:50]}"
    except Exception as e:
        logger.error(f"Excepción verificando justificante: {e}")
        return "⚠️ Comprobante recibido. Pendiente de verificación visual por el administrador."
