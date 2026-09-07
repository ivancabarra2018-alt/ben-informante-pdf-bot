"""
🤖 Accede Gratis | Pronósticos Deportivos & IA VIP (@Accedogratis_bot)
Bot oficial de Pronósticos de Fútbol Reales con IA, Detección de Aciertos y Embudo de Ventas VIP.
Cumplimiento normativo para Telegram Ads (Unión Europea).
"""
import os
import sys
import logging
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode, ChatAction

# Asegurar path
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    BOT_TOKEN, BOT_NAME, BOT_USERNAME, PAYMENT_URL,
    SUPPORT_USER, SUPPORT_URL, FREE_ANALYSIS_LIMIT, PRICE_EUR
)
from database import (
    init_db, upsert_user, get_user, increment_analysis,
    get_all_user_ids, get_stats, set_vip_status,
    get_active_free_pick, get_recent_picks, add_new_pick, mark_pick_result
)
from handlers.ai_expert import consult_tipster_ai
from handlers.content import (
    format_active_pick, format_recent_history, BANKROLL_GUIDE_TEXT,
    VIP_BENEFITS_TEXT, TERMS_TEXT, PRIVACY_TEXT
)

# Logging
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AccedeGratisBot")

# ── Teclados Reutilizables ───────────────────────────────────────────────────

def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚽ Pronóstico del Día (Regalo)", callback_data="view_daily_pick"),
            InlineKeyboardButton("📜 Historial de Aciertos", callback_data="view_history"),
        ],
        [
            InlineKeyboardButton("🤖 Pedir Pronóstico a la IA (2 gratis)", callback_data="btn_ask_ai"),
        ],
        [
            InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL),
        ],
        [
            InlineKeyboardButton("📚 Guía de Bankroll", callback_data="view_bankroll"),
            InlineKeyboardButton("💎 Ventajas VIP", callback_data="view_vip"),
        ],
        [
            InlineKeyboardButton("⚖️ Términos & RGPD", callback_data="view_legal"),
            InlineKeyboardButton("💬 Soporte", url=SUPPORT_URL),
        ]
    ])

def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
    ])

# ── Servidor de Salud y Anti-Hibernación ──────────────────────────────────────

async def keep_alive_pinger():
    """Envía pings periódicos entre los bots para mantener Render 100% activo 24/7."""
    import urllib.request
    urls = [
        "https://ben-informante-pdf-bot.onrender.com/health",
        "https://deportes-analisis-bot.onrender.com/health",
        "https://qr-iformaciones-bot.onrender.com/health"
    ]
    await asyncio.sleep(45)
    while True:
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AntiSleep/1.0)"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    pass
            except Exception as e:
                logger.debug(f"KeepAlive error {url}: {e}")
        await asyncio.sleep(480)  # Cada 8 minutos


async def start_health_server():
    """Permite a Render verificar que el servicio web está activo."""
    port = int(os.environ.get("PORT", 8080))
    async def handle_health(_):
        return web.Response(text="OK - Accede Gratis Tipster Bot Operativo ✅")

    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Health server corriendo en puerto {port}")
    asyncio.create_task(keep_alive_pinger())

# ── Comandos Principales ─────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)
    context.user_data["waiting_for_question"] = False

    welcome_text = (
        f"👋 *¡Hola, {user.first_name}! Bienvenido a Accede Gratis.*\n\n"
        "🎯 *Pronósticos de Fútbol Reales con Inteligencia Artificial:*\n"
        "• ⚽ *Pronóstico del Día gratis:* Partido real analizado con cuota y stake.\n"
        "• 🤖 *2 Pronósticos con IA:* Pídele a la IA el análisis de cualquier partido de hoy.\n"
        "• 💎 *Canal VIP:* Entre 2 y 4 pronósticos diarios verificados por solo 1.99€ al mes.\n\n"
        "👇 *Selecciona una opción para comenzar:*"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Guía de Comandos Oficiales:*\n\n"
        "• /start — Menú interactivo principal\n"
        "• /pronostico — Ver el pronóstico del día gratuito\n"
        "• /historial — Historial de aciertos verificados\n"
        "• /ia — Pedir un pronóstico específico a la IA\n"
        "• /vip — Información y acceso al Canal VIP\n"
        "• /terminos — Términos y condiciones legales\n"
        "• /privacidad — Política de Privacidad RGPD\n"
        "• /soporte — Canal de atención oficial"
    )
    await update.message.reply_text(text, reply_markup=get_back_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def cmd_pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pick = await get_active_free_pick()
    text = format_active_pick(pick)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Pedir Pronóstico de Otro Partido", callback_data="btn_ask_ai")],
        [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    picks = await get_recent_picks(limit=6)
    text = format_recent_history(picks)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ Unirme a la Racha del VIP ({PRICE_EUR})", url=PAYMENT_URL)],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_pregunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u_data = await get_user(user.id)
    used = u_data.get("analysis_used", 0)
    is_vip = u_data.get("is_vip", 0)

    if not is_vip and used >= FREE_ANALYSIS_LIMIT:
        text = (
            "🔒 *Has alcanzado el límite de tu prueba gratuita (2/2 pronósticos).*\\n\\n"
            "Esperamos que la precisión de nuestros análisis te haya demostrado la fuerza del método.\\n\\n"
            "Para continuar recibiendo pronósticos diarios ilimitados y alertas antes de que bajen las cuotas, "
            "entra en nuestro Club VIP:\\n\\n"
            f"💳 *Acceso VIP:* `{PRICE_EUR}`\\n"
            "Sin permanencia obligatoria. Cancela cuando quieras."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    context.user_data["waiting_for_question"] = True
    remaining = "Ilimitados (VIP)" if is_vip else f"{FREE_ANALYSIS_LIMIT - used} disponibles"
    text = (
        "🤖 *Generador de Pronósticos de Fútbol con IA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Consultas de prueba: *{remaining}*\n\n"
        "Escribe qué partido o liga quieres que analice la IA:\n"
        "• *'Dame un pronóstico para el partido de España de hoy'*\n"
        "• *'¿Qué pronóstico ves claro en Champions League esta semana?'*\n"
        "• *'Analízame el Real Madrid vs Real Sociedad con cuota y stake'*\n\n"
        "✍️ *Escribe tu petición aquí abajo:* 👇"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancelar y Volver", callback_data="menu_home")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Adquirir Acceso VIP ({PRICE_EUR})", url=PAYMENT_URL)],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
    ])
    await update.message.reply_text(VIP_BENEFITS_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_terminos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TERMS_TEXT, reply_markup=get_back_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def cmd_privacidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PRIVACY_TEXT, reply_markup=get_back_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await get_stats()
    text = (
        "📊 *Estadísticas del Club VIP:*\n\n"
        f"• Usuarios registrados en el bot: `{stats['total_users']}`\n"
        f"• Pronósticos generados por IA: `{stats['total_analyses']}`\n"
        f"• Total pronósticos auditados: `{stats['total_picks']}`\n"
        f"• Aciertos verificados: `{stats['won_picks']} ({stats['win_rate']}%)`\n"
        f"• Suscriptores VIP activos: `{stats['total_vip']}`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ── Comandos de Gestión y Activación de Ventas ────────────────────────────────

async def cmd_marcar_verde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    DISPARADOR DE VENTAS AUTOMATIZADO:
    Marca el pronóstico activo como ACERTADO y envía automáticamente
    el mensaje de celebración y venta a TODOS los usuarios del bot.
    """
    pick = await get_active_free_pick()
    if not pick:
        await update.message.reply_text("❌ No hay pronóstico activo para marcar.")
        return

    # Marcar como acertado
    updated = await mark_pick_result(pick["id"], "ACERTADO")

    celebration_msg = (
        "🟢 *¡BOOOOOOM! ¡OTRO VERDE MÁS EN EL GRATUITO!* 🟢\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚽ *Partido:* *{updated.get('match_title')}*\n"
        f"🎯 *Selección:* `{updated.get('selection')}`\n"
        f"📈 *Cuota Ganadora:* `{updated.get('odds')}` ✅ ACERTADA\n\n"
        "¿Has visto la efectividad de nuestros modelos con Inteligencia Artificial?\n"
        "En el Canal VIP enviamos entre 2 y 4 selecciones como esta todos los días con análisis completo.\n\n"
        f"👇 *¡Aprovecha la racha y únete hoy al Canal VIP por {PRICE_EUR}!*"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)]
    ])

    all_users = await get_all_user_ids()
    await update.message.reply_text(f"🚀 ¡Marcado como VERDE! Notificando a {len(all_users)} usuarios para activar ventas...")

    sent = 0
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=celebration_msg, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await update.message.reply_text(f"✅ Campaña de ventas enviada: {sent}/{len(all_users)} usuarios notificados con éxito.")

async def cmd_nuevo_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Permite publicar un nuevo pronóstico en 1 segundo:
    Uso: /nuevo_pick Partido | Competicion | Momento | Seleccion | Cuota | Stake | Analisis
    """
    raw = update.message.text.replace("/nuevo_pick", "").strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 7:
        await update.message.reply_text(
            "Uso:\n`/nuevo_pick Partido | Competición | Momento | Selección | Cuota | Stake | Análisis`\n\n"
            "Ejemplo:\n`/nuevo_pick Real Madrid vs Betis | La Liga | Hoy 21:00 | Gana Real Madrid | 1.75 | 1.5 | Ofensiva superior y xG de 2.3.`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    try:
        p_id = await add_new_pick(
            match_title=parts[0],
            competition=parts[1],
            match_date=parts[2],
            selection=parts[3],
            odds=float(parts[4]),
            stake=float(parts[5]),
            analysis=parts[6]
        )
        await update.message.reply_text(f"✅ ¡Nuevo pronóstico oficial #{p_id} registrado como ACTIVO del día!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al guardar pronóstico: {e}")

async def cmd_difusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite al tipster enviar difusiones masivas (promociones, audios, avisos) a todos."""
    msg = update.message.text.replace("/difusion", "").strip()
    if not msg:
        await update.message.reply_text("Uso: `/difusion Tu mensaje promocional aquí`", parse_mode=ParseMode.MARKDOWN)
        return

    all_users = await get_all_user_ids()
    await update.message.reply_text(f"📢 Enviando difusión a {len(all_users)} usuarios...")
    sent = 0
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ Entrar al VIP ({PRICE_EUR})", url=PAYMENT_URL)]
    ])
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=msg, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await update.message.reply_text(f"✅ Difusión completada: {sent}/{len(all_users)} mensajes entregados.")

# ── Manejador de Botones Inline ──────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_home":
        context.user_data["waiting_for_question"] = False
        text = (
            f"🏠 *Menú Principal — {BOT_NAME}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Selecciona una opción del menú:"
        )
        await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    elif data == "view_daily_pick":
        context.user_data["waiting_for_question"] = False
        pick = await get_active_free_pick()
        text = format_active_pick(pick)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Pedir Pronóstico de Otro Partido", callback_data="btn_ask_ai")],
            [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "view_history":
        context.user_data["waiting_for_question"] = False
        picks = await get_recent_picks(limit=6)
        text = format_recent_history(picks)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⭐ Unirme a la Racha del VIP ({PRICE_EUR})", url=PAYMENT_URL)],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "view_bankroll":
        context.user_data["waiting_for_question"] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Preguntar a la IA", callback_data="btn_ask_ai")],
            [InlineKeyboardButton("⚽ Ver Pronóstico del Día", callback_data="view_daily_pick")],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await query.edit_message_text(BANKROLL_GUIDE_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "btn_ask_ai":
        user = update.effective_user
        u_data = await get_user(user.id)
        used = u_data.get("analysis_used", 0)
        is_vip = u_data.get("is_vip", 0)

        if not is_vip and used >= FREE_ANALYSIS_LIMIT:
            text = (
                "🔒 *Has utilizado tus 2 pronósticos gratuitos de prueba.*\n\n"
                "Para seguir recibiendo selecciones de alto valor (+EV), recomendaciones de stake "
                "y todos los pronósticos diarios verificados, entra al Canal VIP:\n\n"
                f"💳 *Tarifa Oficial:* `{PRICE_EUR}`\n"
                "Acceso inmediato. Cancela cuando quieras."
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
            ])
            await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            return

        context.user_data["waiting_for_question"] = True
        remaining = "Ilimitados (VIP)" if is_vip else f"{FREE_ANALYSIS_LIMIT - used} de {FREE_ANALYSIS_LIMIT}"
        text = (
            "🤖 *Consultor de Pronósticos con IA*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Pronósticos disponibles: *{remaining}*\n\n"
            "Escribe qué partido o liga deseas consultar:\n"
            "• ¿Qué pronóstico ves claro en fútbol hoy?\n"
            "• Pronóstico exacto para el partido X.\n\n"
            "✍️ *Por favor, escribe tu petición ahora:* 👇"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="menu_home")]
        ])
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "view_vip":
        context.user_data["waiting_for_question"] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Suscribirme al VIP ({PRICE_EUR})", url=PAYMENT_URL)],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await query.edit_message_text(VIP_BENEFITS_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "view_legal":
        context.user_data["waiting_for_question"] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚖️ Términos de Servicio", callback_data="sub_terms")],
            [InlineKeyboardButton("🔒 Política de Privacidad (RGPD)", callback_data="sub_privacy")],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        text = (
            "📋 *Transparencia Legal y Cumplimiento Normativo (UE)*\n\n"
            "En Accede Gratis operamos con total transparencia conforme a las normativas "
            "europeas de comercio digital y protección de datos.\n\n"
            "Selecciona el documento que deseas consultar:"
        )
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "sub_terms":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Volver a Legal", callback_data="view_legal")],
            [InlineKeyboardButton("🏠 Menú", callback_data="menu_home")]
        ])
        await query.edit_message_text(TERMS_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "sub_privacy":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Volver a Legal", callback_data="view_legal")],
            [InlineKeyboardButton("🏠 Menú", callback_data="menu_home")]
        ])
        await query.edit_message_text(PRIVACY_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# ── Manejador de Mensajes de Texto ───────────────────────────────────────────

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if context.user_data.get("waiting_for_question", False):
        u_data = await get_user(user.id)
        used = u_data.get("analysis_used", 0)
        is_vip = u_data.get("is_vip", 0)

        if not is_vip and used >= FREE_ANALYSIS_LIMIT:
            context.user_data["waiting_for_question"] = False
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
            ])
            await update.message.reply_text(
                "🔒 *Has agotado tus 2 pronósticos gratuitos de prueba.*\n"
                "Para recibir todas las selecciones diarias y alertas en directo entra al VIP:",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await update.message.reply_chat_action(ChatAction.TYPING)
        ai_response = consult_tipster_ai(text)
        new_count = await increment_analysis(user.id)
        context.user_data["waiting_for_question"] = False

        if not is_vip:
            header = f"📊 *[Pronóstico IA de Prueba {new_count} de {FREE_ANALYSIS_LIMIT}]*\n\n"
            if new_count >= FREE_ANALYSIS_LIMIT:
                footer = (
                    "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🎉 *Has completado tus 2 pronósticos de prueba gratuita.*\n"
                    "¿Deseas recibir entre 2 y 4 selecciones verificadas diarias en el Canal VIP?"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
                    [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
                ])
            else:
                footer = (
                    "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💡 *Te queda 1 pronóstico gratuito de prueba.*"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 Realizar mi 2º Pronóstico", callback_data="btn_ask_ai")],
                    [InlineKeyboardButton(f"⭐ Ver Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
                    [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
                ])
        else:
            header = "⭐ *[Pronóstico VIP Ilimitado]*\n\n"
            footer = ""
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Otro Pronóstico", callback_data="btn_ask_ai")],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
            ])

        full_message = f"{header}{ai_response}{footer}"
        await update.message.reply_text(full_message, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    suggest_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Ver Pronóstico del Día", callback_data="view_daily_pick")],
        [InlineKeyboardButton("🤖 Pedir Pronóstico a la IA", callback_data="btn_ask_ai")],
        [InlineKeyboardButton("🏠 Ver Menú Completo", callback_data="menu_home")]
    ])
    await update.message.reply_text(
        "👋 ¡Hola! Si deseas ver el pronóstico oficial de hoy o pedirle uno a la IA, pulsa una opción:",
        reply_markup=suggest_kb
    )

# ── Registro de Comandos en Telegram ─────────────────────────────────────────

async def setup_commands(app: Application):
    commands = [
        BotCommand("start", "🚀 Menú principal del Club VIP"),
        BotCommand("pronostico", "⚽ Pronóstico del Día oficial"),
        BotCommand("historial", "📜 Historial de aciertos verificados"),
        BotCommand("ia", "🤖 Pedir pronóstico con IA"),
        BotCommand("vip", f"⭐ Acceso VIP ({PRICE_EUR})"),
        BotCommand("terminos", "⚖️ Términos y Condiciones"),
        BotCommand("privacidad", "🔒 Política de Privacidad RGPD"),
        BotCommand("soporte", "💬 Atención y soporte"),
    ]
    await app.bot.set_my_commands(commands)
    try:
        await app.bot.set_my_description(
            "Pronósticos Deportivos y Análisis Estadístico de Fútbol con IA. "
            "Detección de Valor Esperado (+EV), gestión de bankroll y acceso directo al Canal VIP."
        )
        await app.bot.set_my_short_description(
            "Pronósticos de Fútbol con IA & Canal VIP."
        )
    except Exception as e:
        logger.warning(f"No se pudo actualizar descripción: {e}")
    logger.info("✅ Comandos y descripciones registrados en Telegram")

# ── Inicialización y Main ───────────────────────────────────────────────────

def build_app() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("pronostico", cmd_pronostico))
    app.add_handler(CommandHandler("historial", cmd_historial))
    app.add_handler(CommandHandler("ia", cmd_pregunta))
    app.add_handler(CommandHandler("vip", cmd_vip))
    app.add_handler(CommandHandler("terminos", cmd_terminos))
    app.add_handler(CommandHandler("privacidad", cmd_privacidad))
    app.add_handler(CommandHandler("soporte", lambda u, c: u.message.reply_text(f"Soporte oficial VIP: {SUPPORT_USER}", reply_markup=get_back_keyboard())))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("marcar_verde", cmd_marcar_verde))
    app.add_handler(CommandHandler("verde", cmd_marcar_verde))
    app.add_handler(CommandHandler("nuevo_pick", cmd_nuevo_pick))
    app.add_handler(CommandHandler("pick", cmd_nuevo_pick))
    app.add_handler(CommandHandler("difusion", cmd_difusion))


    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    return app

async def main():
    logger.info(f"🚀 Iniciando {BOT_NAME}...")
    await init_db()
    logger.info("✅ Base de datos SQLite lista con pronósticos reales")

    try:
        await start_health_server()
    except Exception as e:
        logger.warning(f"No se pudo iniciar health server: {e}")

    app = build_app()
    await app.initialize()
    await setup_commands(app)
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

    logger.info(f"🟢 {BOT_NAME} está en línea y escuchando actualizaciones.")

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("🛑 Apagando bot...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Detenido por el usuario")
