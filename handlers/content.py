"""
Contenidos de conversión, guías y formateadores de pronósticos reales para Accede Gratis Tipster VIP.
"""
from config import PRICE_EUR, SUPPORT_USER, PAYMENT_URL

def format_active_pick(pick: dict) -> str:
    if not pick:
        return (
            "⏳ *Preparando el pronóstico del día...*\n\n"
            "Nuestros analistas y la IA están terminando de procesar las alineaciones de hoy. "
            "Vuelve a consultar en unos minutos o pulsa el botón para preguntar directamente a la IA."
        )
    status = pick.get("status", "PENDIENTE")
    status_label = "⏳ PENDIENTE (En juego o por disputarse)" if status == "PENDIENTE" else ("🟢 ACERTADO / VERDE ✅" if status == "ACERTADO" else "🔴 NO ACERTADO")
    return (
        f"⚽ *PRONÓSTICO OFICIAL GRATUITO DEL DÍA*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 *Competición:* {pick.get('competition', 'Fútbol')}\n"
        f"⚔️ *Partido:* *{pick.get('match_title')}*\n"
        f"📅 *Momento:* {pick.get('match_date')}\n\n"
        f"🎯 *Selección:* `{pick.get('selection')}`\n"
        f"📈 *Cuota:* `{pick.get('odds', 1.85)}`\n"
        f"📊 *Stake:* `{pick.get('stake', 1.5)} / 10`\n"
        f"🚦 *Estado:* *{status_label}*\n\n"
        f"🔍 *Análisis Táctico / Estadístico:*\n"
        f"{pick.get('analysis')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *¿Quieres entre 2 y 4 pronósticos diarios analizados con este método?*\n"
        f"Entra hoy al Canal VIP por {PRICE_EUR} y no te quedes fuera."
    )

def format_recent_history(picks: list[dict]) -> str:
    lines = [
        "📜 *HISTORIAL VERIFICADO DE PRONÓSTICOS*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "Resultados oficiales con total transparencia:\n"
    ]
    for p in picks:
        icon = "🟢" if p.get("status") == "ACERTADO" else ("⏳" if p.get("status") == "PENDIENTE" else "🔴")
        lines.append(
            f"{icon} *{p.get('match_title')}* ({p.get('competition')})\n"
            f"   ↳ Selección: `{p.get('selection')}` @ cuota `{p.get('odds')}`\n"
            f"   ↳ Resultado: *{p.get('status')}*\n"
        )
    lines.append(
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 *Súmate a la racha ganadora del Canal VIP.*\n"
        f"Suscripción completa por {PRICE_EUR}."
    )
    return "\n".join(lines)

BANKROLL_GUIDE_TEXT = (
    "📚 *GUÍA MAESTRA: Cómo Gestionar tu Bankroll como un Profesional*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "El 95% de quienes siguen pronósticos pierden dinero no por fallar selecciones, sino por apostar sin un método de gestión matemática.\n\n"
    "📌 *Las 3 Reglas Sagradas de los Tipsters Profesionales:*\n\n"
    "1️⃣ *La Regla del 1% al 3% (Stake Plano o Proporcional):*\n"
    "Si tu bankroll es de 500€, una unidad (Stake 1) nunca debe superar los 5€ a 10€. Nunca aumentes el stake para recuperar una pérdida.\n\n"
    "2️⃣ *Búsqueda Constante de Valor Esperado (+EV):*\n"
    "Solo se entra a una selección si la probabilidad real calculada por la estadística es mayor que la probabilidad implícita de la casa de apuestas.\n\n"
    "3️⃣ *Visión a Largo Plazo (Yield y Volumen):*\n"
    "Un buen rendimiento profesional se mide tras un bloque de al menos 200 a 500 selecciones, manteniendo un Yield positivo sostenido.\n\n"
    "💡 *Aplica esta disciplina a todas tus decisiones para convertir el deporte en una actividad rentable y controlada.*"
)

VIP_BENEFITS_TEXT = (
    "💎 *Membresía Canal VIP — Pronósticos & Analítica Diaria*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Únete a nuestro club privado de suscriptores y recibe todas las selecciones analizadas al milímetro con Inteligencia Artificial.\n\n"
    "✨ *Todo lo que obtienes con tu acceso VIP:*\n"
    "✅ *Entre 2 y 4 pronósticos diarios:* Mercados de alto valor (+EV) en fútbol, baloncesto y tenis.\n"
    "✅ *Justificación táctica y estadística:* Conoce el motivo matemático detrás de cada jugada.\n"
    "✅ *Stake exacto recomendado:* Para que tu capital crezca con riesgo controlado.\n"
    "✅ *Alertas instantáneas:* Avisos en el momento exacto en que sale la cuota con más ventaja.\n"
    "✅ *Soporte y Asesoría 1 a 1:* Atención directa para dudas sobre cuotas y banca.\n\n"
    f"💳 *Tarifa Oficial:* `{PRICE_EUR}`\n"
    "🔒 *Sin permanencia. Cancela tu suscripción en cualquier instante con total libertad.*"
)

TERMS_TEXT = (
    "⚖️ *Términos y Condiciones del Servicio*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "1. *Objeto del Servicio:*\n"
    "La plataforma 'Accede Gratis' provee información, contenidos formativos y consultoría asistida por IA sobre análisis cuantitativo y estadística deportiva.\n\n"
    "2. *Naturaleza Informativa:*\n"
    "Los análisis y estimaciones de valor tienen carácter analítico y recreativo. Ningún pronóstico deportivo garantiza resultados o beneficios económicos certeros.\n\n"
    "3. *Precios y Facturación:*\n"
    f"El coste de la Membresía VIP es de {PRICE_EUR} (impuestos incluidos en la Unión Europea). No existen recargos ocultos ni permanencia obligatoria.\n\n"
    "4. *Derecho de Desistimiento:*\n"
    "El usuario dispone de un plazo de 14 días naturales para solicitar el reembolso conforme a la Directiva de Consumo de la UE, sujeto a condiciones de uso legítimo.\n\n"
    "5. *Juego Responsable (+18):*\n"
    "El servicio promueve la gestión responsable de capital. Prohibido para menores de edad.\n\n"
    f"📬 Contacto legal: {SUPPORT_USER}"
)

PRIVACY_TEXT = (
    "🔒 *Política de Privacidad y Protección de Datos (RGPD)*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "En estricto cumplimiento del Reglamento General de Protección de Datos (RGPD UE 2016/679):\n\n"
    "1. *Responsable:* Equipo de gestión de Accede Gratis VIP.\n"
    "2. *Datos Tratados:* Identificador de Telegram, nombre de usuario y consultas formuladas.\n"
    "3. *Finalidad:* Controlar el límite de análisis gratuitos de prueba y prestar el servicio solicitado.\n"
    "4. *Tus Derechos:* Puedes solicitar la supresión de tus datos en cualquier momento contactando con el soporte.\n"
    "5. *Confidencialidad:* No comercializamos ni transferimos tus datos a terceros."
)
