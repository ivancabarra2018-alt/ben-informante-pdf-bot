"""
🤖 Accede Gratis | Pronósticos Deportivos & IA VIP (@Accedogratis_bot)
Bot simplificado con pronóstico real de fútbol, explicación de funcionamiento,
detección de aciertos (VERDE) y envío automático del enlace de pago para el siguiente pronóstico.
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
from telegram.constants import ParseMode

# Path
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    BOT_TOKEN, BOT_NAME, PAYMENT_URL,
    SUPPORT_USER, SUPPORT_URL, PRICE_EUR
)
from database import (
    init_db, upsert_user, get_all_user_ids, get_active_pick,
    mark_active_pick_won, set_new_active_pick
)
from handlers.content import (
    format_daily_pick, format_green_celebration, TERMS_TEXT
)

# Logging
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AccedeGratisBot")

# ── Teclados Sencillos (Botones Justos) ──────────────────────────────────────

def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚽ Ver Pronóstico Real de Hoy (Gratis)", callback_data="view_pick"),
        ],
        [
            InlineKeyboardButton(f"⭐ Acceso Canal VIP ({PRICE_EUR})", url=PAYMENT_URL),
        ],
        [
            InlineKeyboardButton("💬 Soporte Oficial", url=SUPPORT_URL),
        ]
    ])

def get_pick_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ Acceso Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
        [InlineKeyboardButton("🏠 Volver al Inicio", callback_data="menu_home")]
    ])

# ── Servidor de Salud y Anti-Hibernación para Render 24/7 ────────────────────

async def keep_alive_pinger():
    """Envía un ping periódico para que los servidores de Render no se duerman nunca."""
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

    welcome_text = (
        f"👋 *¡Hola, {user.first_name}! Bienvenido a Accede Gratis.*\n\n"
        "⚽ *¿Cómo funciona este bot?*\n"
        "Te regalamos un **pronóstico de fútbol 100% REAL de hoy**, analizado con Inteligencia Artificial y datos de cuotas.\n\n"
        "🎯 *La regla es sencilla:*\n"
        "• El primer pronóstico es **GRATIS** para que compruebes nuestra efectividad.\n"
        "• **Si sale VERDE y se acierta**, los siguientes pronósticos y alertas exclusivas serán de pago en nuestro **Canal VIP** por solo 1.99€ al mes.\n\n"
        "👇 *Pulsa el botón para ver el partido real de hoy:*"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pick = await get_active_pick()
    text = format_daily_pick(pick)
    await update.message.reply_text(text, reply_markup=get_pick_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def cmd_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💎 *Canal VIP — Pronósticos Exclusivos de Fútbol con IA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Accede a todas las selecciones diarias analizadas con datos matemáticos y valor esperado (+EV):\n\n"
        "✅ *Entre 2 y 4 pronósticos diarios*\n"
        "✅ *Stake recomendado y análisis detallado*\n"
        "✅ *Alertas antes de que bajen las cuotas*\n\n"
        f"💳 *Tarifa Oficial:* `{PRICE_EUR}`\n"
        "Cancela cuando quieras sin permanencia."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ Entrar al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)],
        [InlineKeyboardButton("🏠 Volver al Inicio", callback_data="menu_home")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_terminos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Volver al Inicio", callback_data="menu_home")]])
    await update.message.reply_text(TERMS_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# ── Activación Automática de Ventas al Salir VERDE ───────────────────────────

async def trigger_green_sales_broadcast(bot, pick: dict) -> int:
    """Envía a TODOS los usuarios la celebración del verde con el enlace de pago."""
    all_users = await get_all_user_ids()
    celebration_text = format_green_celebration(pick)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ Acceder al Canal VIP ({PRICE_EUR})", url=PAYMENT_URL)]
    ])

    sent = 0
    for uid in all_users:
        try:
            await bot.send_message(chat_id=uid, text=celebration_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    logger.info(f"🎉 Notificación de VERDE enviada a {sent}/{len(all_users)} usuarios")
    return sent

async def cmd_verde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    DISPARADOR DE VENTAS:
    Marca el partido de hoy como VERDE y le envía a todos los usuarios
    el mensaje de acierto con el botón de pago de KunfuPay al instante.
    """
    pick = await get_active_pick()
    if not pick:
        await update.message.reply_text("❌ No hay partido activo.")
        return

    updated_pick = await mark_active_pick_won(pick["id"])
    await update.message.reply_text("🚀 ¡Partido marcado como VERDE! Enviando a todos los usuarios el mensaje de acierto y el link de pago VIP...")
    sent = await trigger_green_sales_broadcast(context.bot, updated_pick)
    await update.message.reply_text(f"✅ ¡Completado! {sent} usuarios han recibido el mensaje de acierto con tu link de pago de KunfuPay.")

async def cmd_nuevo_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Permite cambiar el partido del día cuando quieras:
    Uso: /pick Partido | Competicion | Horario | Seleccion | Cuota | Stake | Analisis
    """
    raw = update.message.text.replace("/nuevo_pick", "").replace("/pick", "").strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 7:
        await update.message.reply_text(
            "Uso:\n`/pick Partido | Competición | Horario | Selección | Cuota | Stake | Análisis`\n\n"
            "Ejemplo:\n`/pick Getafe vs Celta | LaLiga | Hoy 19:00 | Menos de 2.5 Goles | 1.65 | 1.5 | Partido cerrado y rigidez táctica.`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    try:
        await set_new_active_pick(
            match_title=parts[0],
            competition=parts[1],
            match_time=parts[2],
            selection=parts[3],
            odds=float(parts[4]),
            stake=float(parts[5]),
            analysis=parts[6]
        )
        await update.message.reply_text(f"✅ ¡Nuevo partido real registrado como ACTIVO de hoy: {parts[0]}!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al guardar partido: {e}")

async def cmd_difusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.replace("/difusion", "").strip()
    if not msg:
        await update.message.reply_text("Uso: `/difusion Mensaje`", parse_mode=ParseMode.MARKDOWN)
        return
    all_users = await get_all_user_ids()
    sent = 0
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"⭐ Entrar al VIP ({PRICE_EUR})", url=PAYMENT_URL)]])
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=msg, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await update.message.reply_text(f"✅ Difusión entregada a {sent}/{len(all_users)} usuarios.")

# ── Callbacks de Botones ─────────────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_home":
        user = update.effective_user
        welcome_text = (
            f"👋 *¡Hola, {user.first_name}! Bienvenido a Accede Gratis.*\n\n"
            "⚽ *¿Cómo funciona este bot?*\n"
            "Te regalamos un **pronóstico de fútbol 100% REAL de hoy**, analizado con Inteligencia Artificial y datos de cuotas.\n\n"
            "🎯 *La regla es sencilla:*\n"
            "• El primer pronóstico es **GRATIS** para que compruebes nuestra efectividad.\n"
            "• **Si sale VERDE y se acierta**, los siguientes pronósticos y alertas exclusivas serán de pago en nuestro **Canal VIP** por solo 1.99€ al mes.\n\n"
            "👇 *Pulsa el botón para ver el partido real de hoy:*"
        )
        await query.edit_message_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

    elif data == "view_pick":
        pick = await get_active_pick()
        text = format_daily_pick(pick)
        await query.edit_message_text(text, reply_markup=get_pick_keyboard(), parse_mode=ParseMode.MARKDOWN)

# ── Registro de Comandos en Telegram ─────────────────────────────────────────

async def setup_commands(app: Application):
    commands = [
        BotCommand("start", "🚀 Inicio y explicación"),
        BotCommand("pronostico", "⚽ Ver pronóstico real de hoy"),
        BotCommand("vip", f"⭐ Acceso Canal VIP ({PRICE_EUR})"),
        BotCommand("terminos", "⚖️ Términos legales"),
    ]
    await app.bot.set_my_commands(commands)
    try:
        await app.bot.set_my_description(
            "Pronósticos de Fútbol Reales con Inteligencia Artificial. "
            "Recibe un pronóstico gratuito del día. Si se acierta, accede al Canal VIP para los siguientes."
        )
        await app.bot.set_my_short_description(
            "Pronósticos de Fútbol Reales con IA & Canal VIP."
        )
    except Exception as e:
        logger.warning(f"No se pudo actualizar descripción: {e}")
    logger.info("✅ Comandos y descripciones registrados en Telegram")

# ── Inicialización y Main ───────────────────────────────────────────────────

def build_app() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("pronostico", cmd_pronostico))
    app.add_handler(CommandHandler("vip", cmd_vip))
    app.add_handler(CommandHandler("terminos", cmd_terminos))
    app.add_handler(CommandHandler("verde", cmd_verde))
    app.add_handler(CommandHandler("marcar_verde", cmd_verde))
    app.add_handler(CommandHandler("pick", cmd_nuevo_pick))
    app.add_handler(CommandHandler("nuevo_pick", cmd_nuevo_pick))
    app.add_handler(CommandHandler("difusion", cmd_difusion))

    app.add_handler(CallbackQueryHandler(callback_handler))

    # Si el usuario envía texto cualquiera, recordarle el botón
    async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 Pulsa el botón para ver el pronóstico gratuito de hoy:",
            reply_markup=get_main_keyboard()
        )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    return app

async def main():
    logger.info(f"🚀 Iniciando {BOT_NAME}...")
    await init_db()
    logger.info("✅ Base de datos SQLite lista con el partido real de hoy")

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
