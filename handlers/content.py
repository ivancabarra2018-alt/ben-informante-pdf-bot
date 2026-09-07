"""
Textos formativos y mensajes de conversión para Accede Gratis Tipster VIP.
"""
from config import PRICE_EUR, PAYMENT_URL, SUPPORT_USER

def format_daily_pick(pick: dict) -> str:
    if not pick:
        return "⏳ El pronóstico de hoy se está procesando. Vuelve a consultar en unos minutos."

    status = pick.get("status", "PENDIENTE")
    status_emoji = "⏳ EN JUEGO / POR DISPUTARSE" if status == "PENDIENTE" else "🟢 ACERTADO ✅"

    return (
        "⚽ *PRONÓSTICO REAL DE FÚTBOL (GRATUITO)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 *Competición:* {pick.get('competition')}\n"
        f"⚔️ *Partido:* *{pick.get('match_title')}*\n"
        f"⏰ *Horario:* {pick.get('match_time')}\n\n"
        f"🎯 *Pronóstico Oficial:* `{pick.get('selection')}`\n"
        f"📈 *Cuota de Valor (+EV):* `{pick.get('odds')}`\n"
        f"📊 *Stake Sugerido:* `{pick.get('stake')} / 10`\n"
        f"🚦 *Estado:* *{status_emoji}*\n\n"
        "🔍 *Análisis Táctico y Estadístico (IA):*\n"
        f"{pick.get('analysis')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *¿Cómo funciona?*\n"
        "Este pronóstico es totalmente gratuito para que compruebes nuestra efectividad. "
        "Si sale *VERDE*, te enviaremos el acceso para adquirir los siguientes pronósticos en el Canal VIP."
    )

def format_green_celebration(pick: dict) -> str:
    return (
        "🟢 *¡BOOOOOOM! ¡PRONÓSTICO DE HOY ACERTADO!* 🟢\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚽ *Partido:* *{pick.get('match_title')}*\n"
        f"🎯 *Selección:* `{pick.get('selection')}`\n"
        f"📈 *Cuota Ganadora:* `{pick.get('odds')}` ✅ *ACERTADA*\n\n"
        "Tal y como te prometimos: te dimos un pronóstico real y ha salido *VERDE*.\n\n"
        "🔥 *¿Quieres los siguientes pronósticos y alertas exclusivas?*\n"
        f"El próximo pronóstico y todos los del mes están disponibles en nuestro **Canal VIP** por {PRICE_EUR}.\n\n"
        "👇 *Haz clic abajo para unirte ahora y no quedarte fuera:*"
    )

TERMS_TEXT = (
    "⚖️ *Términos del Servicio*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "El servicio 'Accede Gratis' ofrece análisis deportivo y contenidos formativos basados en datos estadísticos. "
    f"La suscripción al Canal VIP tiene un coste de {PRICE_EUR} (impuestos incluidos en la UE) sin permanencia. "
    "El usuario dispone de 14 días de desistimiento conforme a la normativa comunitaria. "
    "Prohibido para menores de edad (+18). Juega siempre con responsabilidad.\n\n"
    f"📬 Soporte: {SUPPORT_USER}"
)
