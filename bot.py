"""
🤖 Ben Informante | Academia de Negocios Digitales & Consultoría IA
Bot oficial certificado y optimizado para Telegram Ads (Unión Europea).
"""
import os
import sys
import io
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
    SUPPORT_USER, SUPPORT_URL, OFFICIAL_CHANNEL,
    FREE_QUESTIONS_LIMIT, PRICE_EUR
)
from database import (
    init_db, upsert_user, get_user, increment_question,
    get_all_user_ids, get_stats, set_pro_status
)
from handlers.ai_expert import consult_ai_expert
from handlers.content import (
    LESSON_1_TEXT, LESSON_2_TEXT, ABOUT_SERVICE_TEXT,
    PRO_OFFER_TEXT, TERMS_TEXT, PRIVACY_TEXT
)

# Logging
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("BenInformanteBot")

# ── Teclados Reutilizables ───────────────────────────────────────────────────

def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎓 Lección 1: Automatización", callback_data="view_lesson_1"),
            InlineKeyboardButton("📈 Lección 2: Monetización", callback_data="view_lesson_2"),
        ],
        [
            InlineKeyboardButton("🤖 Consultar al Experto IA (2 gratis)", callback_data="btn_ask_ai"),
        ],
        [
            InlineKeyboardButton(f"⭐ Membresía PRO ({PRICE_EUR})", url=PAYMENT_URL),
        ],
        [
            InlineKeyboardButton("🏢 Sobre el Servicio", callback_data="view_about"),
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

# ── Servidor de Salud para Render ────────────────────────────────────────────

async def start_health_server():
    """Permite a Render verificar que el servicio web está activo."""
    port = int(os.environ.get("PORT", 8080))
    async def handle_health(_):
        return web.Response(text="OK - Ben Informante Bot Operativo ✅")

    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Health server corriendo en puerto {port}")

# ── Comandos Principales ─────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)
    context.user_data["waiting_for_question"] = False

    welcome_text = (
        f"👋 *Bienvenido/a a {BOT_NAME}*, {user.first_name}.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Somos una plataforma formativa y de consultoría ejecutiva para emprendedores, "
        "profesionales y empresas que desean rentabilizar la Inteligencia Artificial.\n\n"
        "🎁 *Tu acceso de bienvenida incluye:*\n"
        "• 📚 *2 Lecciones magistrales completas* de implementación inmediata.\n"
        "• 🤖 *2 Consultas estratégicas gratuitas* atendidas en tiempo real por nuestro motor de Consultoría IA Senior.\n"
        "• 📊 Acceso a las normativas, casos prácticos y soporte oficial.\n\n"
        "👇 *Selecciona una opción del menú inferior para comenzar:*"
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
        "• /lecciones — Acceso a las clases formativas\n"
        "• /pregunta — Formular consulta al Consultor IA\n"
        "• /pro — Información y activación de Membresía PRO\n"
        "• /terminos — Términos y condiciones legales\n"
        "• /privacidad — Política de protección de datos RGPD\n"
        "• /soporte — Canal de atención al cliente"
    )
    await update.message.reply_text(text, reply_markup=get_back_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def cmd_pregunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u_data = await get_user(user.id)
    used = u_data.get("questions_used", 0)
    is_pro = u_data.get("is_pro", 0)

    if not is_pro and used >= FREE_QUESTIONS_LIMIT:
        text = (
            "🔒 *Has alcanzado el límite de tu prueba gratuita (2/2 consultas).*\n\n"
            "Esperamos que las respuestas del Consultor IA hayan aportado claridad a tus proyectos.\n\n"
            "Para continuar formulando preguntas ilimitadas, acceder a más de 20 módulos avanzados "
            "y recibir soporte prioritario, activa tu acceso PRO:\n\n"
            f"💳 *Membresía PRO:* `{PRICE_EUR}`\n"
            "Sin permanencia. Cancela cuando quieras."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⭐ Activar Membresía PRO ({PRICE_EUR})", url=PAYMENT_URL)],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    context.user_data["waiting_for_question"] = True
    remaining = "Ilimitadas (PRO)" if is_pro else f"{FREE_QUESTIONS_LIMIT - used} disponibles"
    text = (
        "🤖 *Consultor Estratégico IA — Sesión Activa*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Consultas de prueba: *{remaining}*\n\n"
        "Escribe a continuación tu duda o proyecto sobre:\n"
        "• Automatización de tareas o integración de APIs.\n"
        "• Modelos de monetización y servicios digitales.\n"
        "• Estrategia de productividad o prompts.\n\n"
        "✍️ *Envía tu mensaje directamente en el chat:* 👇"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancelar y Volver", callback_data="menu_home")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Adquirir Acceso PRO ({PRICE_EUR})", url=PAYMENT_URL)],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
    ])
    await update.message.reply_text(PRO_OFFER_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_terminos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TERMS_TEXT, reply_markup=get_back_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def cmd_privacidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PRIVACY_TEXT, reply_markup=get_back_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await get_stats()
    text = (
        "📊 *Estadísticas de la Academia:*\n\n"
        f"• Usuarios registrados: `{stats['total_users']}`\n"
        f"• Consultas IA generadas: `{stats['total_questions']}`\n"
        f"• Miembros PRO activos: `{stats['total_pro']}`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_difusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite difundir un anuncio a todos los usuarios."""
    user_id = update.effective_user.id
    msg = update.message.text.replace("/difusion", "").strip()
    if not msg:
        await update.message.reply_text("Uso: `/difusion Tu mensaje aquí`", parse_mode=ParseMode.MARKDOWN)
        return

    all_users = await get_all_user_ids()
    await update.message.reply_text(f"📢 Enviando difusión a {len(all_users)} usuarios...")
    sent = 0
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=msg, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await update.message.reply_text(f"✅ Difusión completada: {sent}/{len(all_users)} mensajes entregados.")

# ── Manejador de Botones Inline (Callbacks) ──────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_home":
        context.user_data["waiting_for_question"] = False
        user = update.effective_user
        text = (
            f"🏠 *Menú Principal — {BOT_NAME}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Selecciona la sección a la que deseas acceder:"
        )
        await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    elif data == "view_lesson_1":
        context.user_data["waiting_for_question"] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Consultar al Experto sobre esto", callback_data="btn_ask_ai")],
            [InlineKeyboardButton("📈 Ir a Lección 2", callback_data="view_lesson_2")],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await query.edit_message_text(LESSON_1_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "view_lesson_2":
        context.user_data["waiting_for_question"] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Consultar al Experto sobre esto", callback_data="btn_ask_ai")],
            [InlineKeyboardButton("🎓 Ver Lección 1", callback_data="view_lesson_1")],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await query.edit_message_text(LESSON_2_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "btn_ask_ai":
        user = update.effective_user
        u_data = await get_user(user.id)
        used = u_data.get("questions_used", 0)
        is_pro = u_data.get("is_pro", 0)

        if not is_pro and used >= FREE_QUESTIONS_LIMIT:
            text = (
                "🔒 *Has utilizado tus 2 consultas de prueba gratuita.*\n\n"
                "Para seguir recibiendo asesoría estratégica ilimitada, recomendaciones personalizadas "
                "y plantillas operativas, suscríbete a la Membresía PRO:\n\n"
                f"💳 *Tarifa Oficial:* `{PRICE_EUR}`\n"
                "Total transparencia. Sin compromiso de permanencia."
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"⭐ Activar Membresía PRO ({PRICE_EUR})", url=PAYMENT_URL)],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
            ])
            await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            return

        context.user_data["waiting_for_question"] = True
        remaining = "Ilimitadas (PRO)" if is_pro else f"{FREE_QUESTIONS_LIMIT - used} de {FREE_QUESTIONS_LIMIT}"
        text = (
            "🤖 *Consultoría Estratégica con IA*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Consultas disponibles: *{remaining}*\n\n"
            "Plantea cualquier duda sobre:\n"
            "• Casos reales de automatización en tu negocio.\n"
            "• Validación de ideas o servicios digitales.\n"
            "• Selección de stack tecnológico con IA.\n\n"
            "✍️ *Por favor, escribe tu pregunta ahora:* 👇"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="menu_home")]
        ])
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "view_about":
        context.user_data["waiting_for_question"] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Contactar Soporte", url=SUPPORT_URL)],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await query.edit_message_text(ABOUT_SERVICE_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "view_legal":
        context.user_data["waiting_for_question"] = False
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚖️ Términos de Servicio", callback_data="sub_terms")],
            [InlineKeyboardButton("🔒 Política de Privacidad (RGPD)", callback_data="sub_privacy")],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        text = (
            "📋 *Transparencia Legal y Cumplimiento Normativo (UE)*\n\n"
            "En Ben Informante operamos con estricto apego a las directivas de consumo "
            "y protección de datos de la Unión Europea.\n\n"
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

    # Si está en modo consulta activa
    if context.user_data.get("waiting_for_question", False):
        u_data = await get_user(user.id)
        used = u_data.get("questions_used", 0)
        is_pro = u_data.get("is_pro", 0)

        if not is_pro and used >= FREE_QUESTIONS_LIMIT:
            context.user_data["waiting_for_question"] = False
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"⭐ Activar Membresía PRO ({PRICE_EUR})", url=PAYMENT_URL)],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
            ])
            await update.message.reply_text(
                "🔒 *Has agotado tus 2 consultas gratuitas.*\n"
                "Para consultar sin límites activa tu membresía PRO:",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Enviar acción escribiendo
        await update.message.reply_chat_action(ChatAction.TYPING)

        # Consultar a la IA
        ai_response = consult_ai_expert(text)

        # Registrar consulta
        new_count = await increment_question(user.id)
        context.user_data["waiting_for_question"] = False

        if not is_pro:
            header = f"📊 *[Consulta de Prueba {new_count} de {FREE_QUESTIONS_LIMIT}]*\n\n"
            if new_count >= FREE_QUESTIONS_LIMIT:
                footer = (
                    "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🎉 *Has completado tus 2 consultas de prueba gratuita.*\n"
                    "¿Deseas seguir acelerando tus proyectos con consultoría ilimitada?"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"⭐ Suscribirme a PRO ({PRICE_EUR})", url=PAYMENT_URL)],
                    [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
                ])
            else:
                footer = (
                    "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💡 *Te queda 1 consulta gratuita.*"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 Realizar mi 2ª Consulta", callback_data="btn_ask_ai")],
                    [InlineKeyboardButton("⭐ Ver Membresía PRO", url=PAYMENT_URL)],
                    [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
                ])
        else:
            header = "⭐ *[Consultoría PRO Ilimitada]*\n\n"
            footer = ""
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Otra Consulta", callback_data="btn_ask_ai")],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
            ])

        full_message = f"{header}{ai_response}{footer}"
        await update.message.reply_text(full_message, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # Mensaje de texto casual sin haber pulsado el botón
    suggest_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Preguntar al Experto IA", callback_data="btn_ask_ai")],
        [InlineKeyboardButton("🏠 Ver Menú Completo", callback_data="menu_home")]
    ])
    await update.message.reply_text(
        "👋 ¡Hola! Si deseas formular una consulta sobre negocios o IA, pulsa el botón inferior:",
        reply_markup=suggest_kb
    )

# ── Registro de Comandos en Telegram ─────────────────────────────────────────

async def setup_commands(app: Application):
    commands = [
        BotCommand("start", "🚀 Menú principal de la Academia"),
        BotCommand("lecciones", "📚 Ver las lecciones magistrales"),
        BotCommand("pregunta", "🤖 Consultar al Experto IA"),
        BotCommand("pro", f"⭐ Membresía PRO ({PRICE_EUR})"),
        BotCommand("terminos", "⚖️ Términos y Condiciones"),
        BotCommand("privacidad", "🔒 Política de Privacidad RGPD"),
        BotCommand("soporte", "💬 Contacto y atención"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("✅ 7 comandos oficiales registrados en Telegram")

# ── Inicialización y Main ───────────────────────────────────────────────────

def build_app() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("lecciones", lambda u, c: u.message.reply_text("Elige lección:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 Lección 1", callback_data="view_lesson_1")],
        [InlineKeyboardButton("📈 Lección 2", callback_data="view_lesson_2")]
    ]))))
    app.add_handler(CommandHandler("pregunta", cmd_pregunta))
    app.add_handler(CommandHandler("pro", cmd_pro))
    app.add_handler(CommandHandler("terminos", cmd_terminos))
    app.add_handler(CommandHandler("privacidad", cmd_privacidad))
    app.add_handler(CommandHandler("soporte", lambda u, c: u.message.reply_text(f"Atención al cliente: {SUPPORT_USER}", reply_markup=get_back_keyboard())))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("difusion", cmd_difusion))

    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Mensajes de texto
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    return app

async def main():
    logger.info(f"🚀 Iniciando {BOT_NAME}...")
    await init_db()
    logger.info("✅ Base de datos SQLite lista")

    # Iniciar servidor de health check
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
