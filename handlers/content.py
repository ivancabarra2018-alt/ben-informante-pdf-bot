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
        f"📈 *Cuota Real (+EV):* `{pick.get('odds', 1.0)}`\n"
        f"📊 *Stake Sugerido:* `{pick.get('stake', 1.0)} / 10`\n"
        f"🚦 *Estado:* *{status_emoji}*\n\n"
        "🔍 *Análisis Táctico y Estadístico (IA):*\n"
        f"{pick.get('analysis', 'Sin análisis detallado.')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Transparencia y Reglas:*\n"
        "• Este pronóstico es **100% GRATIS** para que compruebes nuestra efectividad con un partido real.\n"
        f"• **Si sale VERDE**, la Apuesta del Día Siguiente (Mañana) será de pago por **{PRICE_EUR}**.\n"
        "• **Si se falla**, los nuevos y los que pagaron recibirán el siguiente día **GRATIS** sin pagar."
    )

def format_paid_pick(pick: dict) -> str:
    if not pick:
        return "⏳ La apuesta del día siguiente se está preparando. Se publicará en breve."

    return (
        "👑 *APUESTA DEL DÍA SIGUIENTE (MAÑANA) | ACCESO PAGADO*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 *Competición:* {pick.get('competition', 'UEFA Champions League')}\n"
        f"⚔️ *Partido:* *{pick.get('match_title', 'Partido de Mañana')}*\n"
        f"⏰ *Horario:* {pick.get('match_time', 'Mañana a las 21:00 h')}\n\n"
        f"🎯 *Pronóstico Oficial:* `{pick.get('selection', '')}`\n"
        f"📈 *Cuota Real de Mercado:* `{pick.get('odds', 1.0)}`\n"
        f"📊 *Stake Asignado:* `{pick.get('stake', 1.0)} / 10`\n\n"
        "🔍 *Informe Técnico Confidencial (IA):*\n"
        f"{pick.get('analysis', '')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 *¡Gracias por tu pago! Tu bot ha sido reseteado y tienes la apuesta de mañana garantizada.*"
    )

def format_exhausted_free_pick(payment_url: str) -> str:
    return (
        "⛔ *YA HAS CONSUMIDO TU PRONÓSTICO GRATUITO DE PRUEBA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Ya disfrutaste de tu pronóstico gratuito anteriormente.\n\n"
        f"Para desbloquear la **Apuesta del Día Siguiente (Mañana)** analizada con Inteligencia Artificial:\n\n"
        f"1️⃣ Realiza el pago de **{PRICE_EUR}**: [Enlace Oficial KunfuPay]({payment_url})\n"
        "2️⃣ Envía la captura del justificante de pago en este chat.\n\n"
        "🔄 *Al verificar tu comprobante, tu bot se reseteará de inmediato para entregarte la apuesta de mañana.*"
    )

def format_green_celebration(pick: dict, payment_url: str) -> str:
    return (
        "🟢 *¡BOOOOOOM! ¡PRONÓSTICO DE HOY ACERTADO (VERDE)!* 🟢\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚽ *Partido:* *{pick.get('match_title', 'Partido')}*\n"
        f"🎯 *Selección:* `{pick.get('selection', '')}`\n"
        f"📈 *Cuota Ganadora:* `{pick.get('odds', '')}` ✅ *ACERTADA*\n\n"
        "¡Tal y como te prometimos, el pronóstico real de hoy ha salido *VERDE*!\n\n"
        f"🔥 *¿Quieres la Apuesta del Día Siguiente (Mañana)?*\n"
        f"Ya tenemos listo el pronóstico de mañana con máximo valor estadístico por solo **{PRICE_EUR}**.\n\n"
        f"💳 *Paso 1:* Realiza el pago en [KunfuPay Oficial]({payment_url})\n"
        "🧾 *Paso 2:* Envía la captura del justificante en este chat para **resetear tu bot** y recibir la apuesta de mañana."
    )

def format_red_compensation(pick: dict) -> str:
    return (
        "🔴 *RESULTADO DEL PRONÓSTICO: NO SE DIO (ROJO)* 🔴\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚽ *Partido:* *{pick.get('match_title', 'Partido')}*\n"
        f"🎯 *Selección:* `{pick.get('selection', '')}`\n"
        "❌ *Resultado:* No se cumplió el pronóstico.\n\n"
        "🛡️ *COMPENSACIÓN Y GARANTÍA DE TRANSPARENCIA:*\n"
        "Aquí trabajamos con honestidad real. Al no haberse acertado el pronóstico de hoy, **hemos reseteado el bot** a los nuevos usuarios y a los que comprasteis.\n\n"
        "🎁 *La apuesta del día de mañana será 100% GRATIS para vosotros sin pagar nada.*\n"
        "Mañana podréis consultarla directamente en el bot."
    )

def format_receipt_instructions(payment_url: str) -> str:
    return (
        "🧾 *VALIDACIÓN DE JUSTIFICANTE DE PAGO*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Para desbloquear la **Apuesta del Día Siguiente ({PRICE_EUR})**:\n\n"
        f"1️⃣ Accede al pago oficial: [Enlace de Pago KunfuPay]({payment_url})\n"
        f"2️⃣ Completa el importe ({PRICE_EUR})\n"
        "3️⃣ **Envía en este chat una foto o captura de pantalla** del comprobante o justificante.\n\n"
        "🤖 *El administrador validará tu comprobante, tu bot se reseteará y recibirás de inmediato la apuesta de mañana.*"
    )

TERMS_TEXT = (
    "⚖️ *Términos del Servicio*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "El servicio 'Accede Gratis' ofrece análisis deportivo y pronósticos basados en datos estadísticos y modelos de Inteligencia Artificial. "
    f"El acceso a la apuesta de cada día tiene un coste de {PRICE_EUR} (impuestos incluidos en la UE) sin suscripción forzada. "
    "El usuario dispone de derecho de desistimiento conforme a la normativa comunitaria vigente. "
    "Prohibido para menores de edad (+18). Juega siempre con responsabilidad.\n\n"
    f"📬 Soporte: {SUPPORT_USER}"
)
