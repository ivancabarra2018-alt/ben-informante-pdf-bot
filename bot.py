"""
🤖 Accede Gratis | Pronósticos Deportivos & IA VIP (@Accedogratis_bot)
Bot oficial de Embudo de Conversión para Tipster con Inteligencia Artificial.
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
    get_all_user_ids, get_stats, set_vip_status
)
from handlers.ai_expert import consult_tipster_ai
from handlers.content import (
    DAILY_TIP_TEXT, BANKROLL_GUIDE_TEXT, VIP_BENEFITS_TEXT,
    TERMS_TEXT, PRIVACY_TEXT
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
            InlineKeyboardButton("🎁 Análisis del Día (Regalo)", callback_data="view_daily_tip"),
            InlineKeyboardButton("📚 Guía Bankroll & Stake", callback_data="view_bankroll"),
        ],
        [
            InlineKeyboardButton("🤖 Pedir Análisis al Experto IA (2 gratis)", callback_data="btn_ask_ai"),
        ],
        [
            InlineKeyboardButton(f"⭐ Acceso Canal VIP ({PRICE_EUR})", url=PAYMENT_URL),
        ],
        [
            InlineKeyboardButton("💎 Ventajas del VIP", callback_data="view_vip"),
            InlineKeyboardButton("⚖️ Términos & RGPD", callback_data="view_legal"),
        ],
        [
            InlineKeyboardButton("💬 Soporte Oficial", url=SUPPORT_URL),
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
        "🎯 *Tu Analista y Embudo de Pronósticos Deportivos con IA:*\n"
        "• 🎁 *Análisis del Día:* Análisis táctico y estadístico de regalo.\n"
        "• 🤖 *2 Análisis con IA gratis:* Pregúntale a la IA sobre cualquier partido o cuota.\n"
        "• 💎 *Acceso Canal VIP:* Pronósticos diarios de alto valor por solo 1.99€ al mes.\n\n"
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
        "• /regalo — Ver el análisis del día gratuito\n"
        "• /analisis — Formular consulta al Analista IA\n"
        "• /vip — Información del Canal VIP\n"
        "• /terminos — Términos y condiciones legales\n"
        "• /privacidad — Política de Privacidad RGPD\n"
        "• /soporte — Canal de atención oficial"
    )
    await update.message.reply_text(text, reply_markup=get_back_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def cmd_pregunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u_data = await get_user(user.id)
    used = u_data.get("analysis_used", 0)
    is_vip = u_data.get("is_vip", 0)

    if not is_vip and used >= FREE_ANALYSIS_LIMIT:
        text = (
            "🔒 *Has alcanzado el límite de tu prueba gratuita (2/2 análisis).*\n\n"
            "Esperamos que los informes de Valor Esperado (+EV) hayan demostrado la potencia de nuestro método.\n\n"
            "Para continuar recibiendo análisis ilimitados de cualquier evento y acceder a todos los pronósticos diarios, "
            "entra en nuestro Club VIP:\n\n"
            f"💳 *Acceso VIP:* `{PRICE_EUR}`\n"
            "Sin permanencia obligatoria. Cancela en cualquier instante."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    context.user_data["waiting_for_question"] = True
    remaining = "Ilimitadas (VIP)" if is_vip else f"{FREE_ANALYSIS_LIMIT - used} disponibles"
    text = (
        "🤖 *Analista Deportivo IA — Consulta Activa*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Análisis de prueba: *{remaining}*\n\n"
        "Indica qué partido, cuota o mercado deseas que analice la IA:\n"
        "• Ejemplo: *'¿Tiene valor apostar a victoria del Arsenal a cuota 1.85?'*\n"
        "• Ejemplo: *'Análisis del partido Barcelona vs Nápoles en Champions'*\n\n"
        "✍️ *Escribe tu pregunta directamente a continuación:* 👇"
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
        "📊 *Estadísticas del Embudo VIP:*\n\n"
        f"• Usuarios registrados en el bot: `{stats['total_users']}`\n"
        f"• Análisis generados por IA: `{stats['total_analyses']}`\n"
        f"• Suscriptores VIP activos: `{stats['total_vip']}`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_difusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite al tipster enviar difusiones masivas (promociones, resumen de verdes) a todos."""
    msg = update.message.text.replace("/difusion", "").strip()
    if not msg:
        await update.message.reply_text("Uso: `/difusion Tu mensaje promocional aquí`", parse_mode=ParseMode.MARKDOWN)
        return

    all_users = await get_all_user_ids()
    await update.message.reply_text(f"📢 Enviando difusión a {len(all_users)} usuarios del bot...")
    sent = 0
    for uid in all_users:
        try:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"⭐ Entrar al VIP ({PRICE_EUR})", url=PAYMENT_URL)]
            ])
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

    elif data == "view_daily_tip":
        context.user_data["waiting_for_question"] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Consultar al Experto sobre esto", callback_data="btn_ask_ai")],
            [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await query.edit_message_text(DAILY_TIP_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "view_bankroll":
        context.user_data["waiting_for_question"] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Preguntar Dudas a la IA", callback_data="btn_ask_ai")],
            [InlineKeyboardButton("🎁 Ver Análisis del Día", callback_data="view_daily_tip")],
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
                "🔒 *Has utilizado tus 2 análisis de prueba gratuita.*\n\n"
                "Para seguir recibiendo informes de Valor Esperado (+EV), recomendaciones de stake "
                "y todos los pronósticos verificados, entra al Canal VIP:\n\n"
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
        remaining = "Ilimitadas (VIP)" if is_vip else f"{FREE_ANALYSIS_LIMIT - used} de {FREE_ANALYSIS_LIMIT}"
        text = (
            "🤖 *Consultoría de Pronósticos con IA*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Análisis disponibles: *{remaining}*\n\n"
            "Pregúntale a la IA sobre cualquier partido, cuota o mercado:\n"
            "• ¿Tiene valor la cuota de X equipo?\n"
            "• Tendencia de goles o puntos para hoy.\n"
            "• Stake recomendado según el riesgo.\n\n"
            "✍️ *Por favor, escribe tu consulta ahora:* 👇"
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
                "🔒 *Has agotado tus 2 análisis gratuitos.*\n"
                "Para recibir pronósticos diarios y análisis ilimitados entra al VIP:",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await update.message.reply_chat_action(ChatAction.TYPING)
        ai_response = consult_tipster_ai(text)
        new_count = await increment_analysis(user.id)
        context.user_data["waiting_for_question"] = False

        if not is_vip:
            header = f"📊 *[Informe de Valor IA {new_count} de {FREE_ANALYSIS_LIMIT}]*\n\n"
            if new_count >= FREE_ANALYSIS_LIMIT:
                footer = (
                    "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🎉 *Has completado tus 2 análisis de prueba gratuita.*\n"
                    "¿Deseas recibir todas las selecciones verificadas del día en el Canal VIP?"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
                    [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
                ])
            else:
                footer = (
                    "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💡 *Te queda 1 análisis gratuito de prueba.*"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 Realizar mi 2º Análisis", callback_data="btn_ask_ai")],
                    [InlineKeyboardButton(f"⭐ Ver Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
                    [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
                ])
        else:
            header = "⭐ *[Análisis VIP Ilimitado]*\n\n"
            footer = ""
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Otro Análisis", callback_data="btn_ask_ai")],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
            ])

        full_message = f"{header}{ai_response}{footer}"
        await update.message.reply_text(full_message, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    suggest_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Ver Análisis de Regalo", callback_data="view_daily_tip")],
        [InlineKeyboardButton("🤖 Pedir Análisis IA", callback_data="btn_ask_ai")],
        [InlineKeyboardButton("🏠 Ver Menú Completo", callback_data="menu_home")]
    ])
    await update.message.reply_text(
        "👋 ¡Hola! Si deseas consultar un pronóstico o ver el análisis del día, pulsa una opción:",
        reply_markup=suggest_kb
    )

# ── Registro de Comandos en Telegram ─────────────────────────────────────────

async def setup_commands(app: Application):
    commands = [
        BotCommand("start", "🚀 Menú principal del Club VIP"),
        BotCommand("regalo", "🎁 Análisis del Día gratuito"),
        BotCommand("analisis", "🤖 Pedir Análisis al Experto IA"),
        BotCommand("vip", f"⭐ Acceso VIP ({PRICE_EUR})"),
        BotCommand("terminos", "⚖️ Términos y Condiciones"),
        BotCommand("privacidad", "🔒 Política de Privacidad RGPD"),
        BotCommand("soporte", "💬 Atención y dudas"),
    ]
    await app.bot.set_my_commands(commands)
    try:
        await app.bot.set_my_description(
            "Comunidad Privada y Análisis Estadístico de Pronósticos Deportivos con IA. "
            "Detección de Valor Esperado (+EV), gestión de bankroll y pronósticos diarios verificados."
        )
        await app.bot.set_my_short_description(
            "Pronósticos Deportivos con IA & Acceso al Canal VIP."
        )
    except Exception as e:
        logger.warning(f"No se pudo actualizar descripción: {e}")
    logger.info("✅ Comandos y descripciones de Tipster VIP registrados en Telegram")

# ── Inicialización y Main ───────────────────────────────────────────────────

def build_app() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("regalo", lambda u, c: u.message.reply_text(DAILY_TIP_TEXT, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ Entrar al VIP ({PRICE_EUR})", url=PAYMENT_URL)]
    ]), parse_mode=ParseMode.MARKDOWN)))
    app.add_handler(CommandHandler("analisis", cmd_pregunta))
    app.add_handler(CommandHandler("vip", cmd_vip))
    app.add_handler(CommandHandler("terminos", cmd_terminos))
    app.add_handler(CommandHandler("privacidad", cmd_privacidad))
    app.add_handler(CommandHandler("soporte", lambda u, c: u.message.reply_text(f"Soporte oficial VIP: {SUPPORT_USER}", reply_markup=get_back_keyboard())))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("difusion", cmd_difusion))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    return app

async def main():
    logger.info(f"🚀 Iniciando {BOT_NAME}...")
    await init_db()
    logger.info("✅ Base de datos SQLite lista")

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
