"""
Textos formativos y mensajes de conversión para Accede Gratis Tipster Pro.
"""
from config import PRICE_EUR, SUPPORT_USER

def format_daily_pick(pick: dict) -> str:
    if not pick:
        return "⏳ El pronóstico gratuito de hoy se está procesando. Vuelve a consultar en unos minutos."

    status = pick.get("status", "PENDIENTE")
    status_emoji = "⏳ POR DISPUTARSE" if status == "PENDIENTE" else ("🟢 ACERTADO ✅" if status == "ACERTADO" else "🔴 FALLADO ❌")

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
        "💡 *Transparencia y Reglas:*\n"
        "• Este pronóstico es **GRATIS** para que compruebes nuestra efectividad con un partido real.\n"
        f"• **Si sale VERDE**, el Siguiente Pronóstico será de pago por solo {PRICE_EUR}.\n"
        "• **Si se falla**, tu bot se reseteará para que el siguiente día lo recibas **GRATIS** sin pagar nada."
    )

def format_paid_pick(pick: dict) -> str:
    if not pick:
        return "⏳ El siguiente pronóstico se está preparando. Se publicará en breve."

    return (
        "👑 *SIGUIENTE PRONÓSTICO EXCLUSIVO (ACCESO PAGADO)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 *Competición:* {pick.get('competition', 'Fútbol')}\n"
        f"⚔️ *Partido:* *{pick.get('match_title', 'Partido')}*\n"
        f"⏰ *Horario:* {pick.get('match_time', 'Próxima jornada')}\n\n"
        f"🎯 *Pronóstico Oficial:* `{pick.get('selection', '')}`\n"
        f"📈 *Cuota de Alto Valor:* `{pick.get('odds', 1.0)}`\n"
        f"📊 *Stake Asignado:* `{pick.get('stake', 1.0)} / 10`\n\n"
        "🔍 *Informe Técnico Confidencial (IA):*\n"
        f"{pick.get('analysis', '')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 *¡Gracias por tu compra! Tu acceso ha sido registrado.*"
    )

def format_exhausted_free_pick(payment_url: str) -> str:
    return (
        "⛔ *YA HAS CONSUMIDO TU PRONÓSTICO GRATUITO DE PRUEBA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Nuestra política te permite probar 1 pronóstico real totalmente gratis.\n\n"
        f"Para desbloquear el **Siguiente Pronóstico** analizado con Inteligencia Artificial:\n\n"
        f"1️⃣ Realiza el pago de **{PRICE_EUR}**: [Enlace Oficial KunfuPay]({payment_url})\n"
        "2️⃣ Envía la captura del justificante de pago en este chat.\n\n"
        "🔄 *Al verificar tu pago, tu bot se reseteará de inmediato para que veas el siguiente pronóstico.*"
    )

def format_green_celebration(pick: dict, payment_url: str) -> str:
    return (
        "🟢 *¡BOOOOOOM! ¡PRONÓSTICO DE HOY ACERTADO (VERDE)!* 🟢\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚽ *Partido:* *{pick.get('match_title', 'Partido')}*\n"
        f"🎯 *Selección:* `{pick.get('selection', '')}`\n"
        f"📈 *Cuota Ganadora:* `{pick.get('odds', '')}` ✅ *ACERTADA*\n\n"
        "Tal y como te prometimos: te dimos un partido 100% real y ha salido *VERDE*.\n\n"
        f"🔥 *¿Quieres el Siguiente Pronóstico de hoy/mañana?*\n"
        f"Ya está seleccionado el próximo partido de alto valor estadístico por solo **{PRICE_EUR}**.\n\n"
        f"💳 *Paso 1:* Realiza el pago en [KunfuPay Oficial]({payment_url})\n"
        "🧾 *Paso 2:* Envía la captura del justificante en este chat para **resetear tu bot** y acceder al pronóstico."
    )

def format_red_compensation(pick: dict) -> str:
    return (
        "🔴 *RESULTADO DEL PRONÓSTICO: NO SE DIO (ROJO)* 🔴\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚽ *Partido:* *{pick.get('match_title', 'Partido')}*\n"
        f"🎯 *Selección:* `{pick.get('selection', '')}`\n"
        "❌ *Resultado:* No se cumplió el pronóstico.\n\n"
        "🛡️ *COMPENSACIÓN Y TRANSPARENCIA TOTAL:*\n"
        "Aquí no ocultamos resultados. Al no haberse acertado el pronóstico de hoy, **hemos reseteado el bot a todos los usuarios** (tanto a los nuevos como a los que comprasteis).\n\n"
        "🎁 *El pronóstico del día siguiente será 100% GRATIS para ti sin pagar nada.*\n"
        "Mañana podrás consultarlo directamente desde el bot."
    )

def format_receipt_instructions(payment_url: str) -> str:
    return (
        "🧾 *VALIDACIÓN DE JUSTIFICANTE DE PAGO*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Para desbloquear el **Siguiente Pronóstico ({PRICE_EUR})**:\n\n"
        f"1️⃣ Accede al pago oficial: [Enlace de Pago KunfuPay]({payment_url})\n"
        f"2️⃣ Completa el importe ({PRICE_EUR})\n"
        "3️⃣ **Envía en este chat una foto o captura de pantalla** del comprobante o justificante.\n\n"
        "🤖 *Nuestra IA evaluará el justificante y el administrador reseteará tu bot para darte acceso al siguiente pronóstico.*"
    )

TERMS_TEXT = (
    "⚖️ *Términos del Servicio*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "El servicio 'Accede Gratis' ofrece análisis deportivo y pronósticos basados en datos estadísticos y modelos de Inteligencia Artificial. "
    f"El acceso a cada siguiente pronóstico tiene un coste de {PRICE_EUR} (impuestos incluidos en la UE) sin suscripción recurrente forzada. "
    "El usuario dispone de derecho de desistimiento conforme a la normativa comunitaria vigente. "
    "Prohibido para menores de edad (+18). Juega siempre con responsabilidad.\n\n"
    f"📬 Soporte: {SUPPORT_USER}"
)
