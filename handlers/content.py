"""
Textos formativos y mensajes de conversión para Accede Gratis Tipster VIP.
"""
from config import PRICE_EUR, SUPPORT_USER

def format_daily_pick(pick: dict) -> str:
    if not pick:
        return "⏳ El pronóstico gratuito de hoy se está procesando. Vuelve a consultar en unos minutos."

    status = pick.get("status", "PENDIENTE")
    status_emoji = "⏳ POR DISPUTARSE" if status == "PENDIENTE" else ("🟢 ACERTADO ✅" if status == "ACERTADO" else "❌ FALLADO")

    return (
        "⚽ *PRONÓSTICO REAL DE FÚTBOL (GRATUITO)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 *Competición:* {pick.get('competition', 'Fútbol')}\n"
        f"⚔️ *Partido:* *{pick.get('match_title', 'Partido del Día')}*\n"
        f"⏰ *Horario:* {pick.get('match_time', 'Hoy')}\n\n"
        f"🎯 *Pronóstico Oficial:* `{pick.get('selection', '')}`\n"
        f"📈 *Cuota de Valor (+EV):* `{pick.get('odds', 1.0)}`\n"
        f"📊 *Stake Sugerido:* `{pick.get('stake', 1.0)} / 10`\n"
        f"🚦 *Estado:* *{status_emoji}*\n\n"
        "🔍 *Análisis Táctico y Estadístico (IA):*\n"
        f"{pick.get('analysis', 'Sin análisis detallado.')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *¿Cómo funciona?*\n"
        "Este pronóstico es totalmente gratuito para que compruebes nuestra efectividad en partidos reales. "
        "Si sale *VERDE*, te daremos acceso al siguiente pronóstico exclusivo mediante el enlace de pago."
    )

def format_vip_pick(pick: dict) -> str:
    if not pick:
        return "⏳ El siguiente pronóstico VIP se está preparando. Se publicará en breve."

    return (
        "👑 *SIGUIENTE PRONÓSTICO EXCLUSIVO (ACCESO VIP)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 *Competición:* {pick.get('competition', 'Fútbol')}\n"
        f"⚔️ *Partido:* *{pick.get('match_title', 'Partido VIP')}*\n"
        f"⏰ *Horario:* {pick.get('match_time', 'Próxima jornada')}\n\n"
        f"🎯 *Pronóstico Oficial VIP:* `{pick.get('selection', '')}`\n"
        f"📈 *Cuota de Alto Valor:* `{pick.get('odds', 1.0)}`\n"
        f"📊 *Stake Asignado:* `{pick.get('stake', 1.0)} / 10`\n\n"
        "🔍 *Informe Técnico Confidencial (IA):*\n"
        f"{pick.get('analysis', '')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 *¡Gracias por tu confianza en nuestro servicio VIP!*"
    )

def format_green_celebration(pick: dict, payment_url: str) -> str:
    return (
        "🟢 *¡BOOOOOOM! ¡PRONÓSTICO DE HOY ACERTADO!* 🟢\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚽ *Partido:* *{pick.get('match_title', 'Partido')}*\n"
        f"🎯 *Selección:* `{pick.get('selection', '')}`\n"
        f"📈 *Cuota Ganadora:* `{pick.get('odds', '')}` ✅ *ACERTADA (VERDE)*\n\n"
        "Tal y como te prometimos: te dimos un pronóstico real y ha salido *VERDE*.\n\n"
        "🔥 *¿Quieres el siguiente pronóstico exclusivo?*\n"
        f"Ya está listo el siguiente pronóstico con máximo valor matemático por tan solo {PRICE_EUR}.\n\n"
        f"💳 *Paso 1:* Realiza el pago en [KunfuPay Oficial]({payment_url})\n"
        "🧾 *Paso 2:* Envía la captura o foto del justificante de pago en este chat para validarlo al instante."
    )

def format_receipt_instructions(payment_url: str) -> str:
    return (
        "🧾 *VALIDACIÓN DE JUSTIFICANTE DE PAGO*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Para acceder a la siguiente apuesta exclusiva VIP:\n\n"
        f"1️⃣ Accede al pago oficial: [Enlace de Pago KunfuPay]({payment_url})\n"
        f"2️⃣ Completa el importe ({PRICE_EUR})\n"
        "3️⃣ **Envía en este chat una foto o captura de pantalla** del comprobante o justificante.\n\n"
        "🤖 *Nuestra Inteligencia Artificial verificará el documento y el administrador activará tu acceso VIP inmediatamente.*"
    )

TERMS_TEXT = (
    "⚖️ *Términos del Servicio*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "El servicio 'Accede Gratis' ofrece análisis deportivo y contenidos formativos basados en datos estadísticos y modelos de Inteligencia Artificial. "
    f"La suscripción al servicio tiene un coste de {PRICE_EUR} (impuestos incluidos en la UE) sin permanencia. "
    "El usuario dispone de 14 días de desistimiento conforme a la normativa comunitaria. "
    "Prohibido para menores de edad (+18). Juega siempre con responsabilidad.\n\n"
    f"📬 Soporte: {SUPPORT_USER}"
)
