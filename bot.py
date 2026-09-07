"""
🤖 Accede Gratis | Pronósticos Deportivos & IA VIP (@Accedogratis_bot)
Bot tipster profesional con pronóstico diario real, sistema de conversión a VIP,
verificación de justificantes de pago con IA (Gemini Vision) y panel secreto /admintg.
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

# Asegurar path
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    BOT_TOKEN, BOT_NAME, PRICE_EUR,
    SUPPORT_USER, SUPPORT_URL
)
from database import (
    init_db, upsert_user, get_user, is_admin_user, get_admin_user_ids,
    get_all_users, get_all_user_ids, get_payment_url, set_payment_url,
    get_free_pick, get_vip_next_pick, mark_free_pick_won,
    set_new_free_pick, set_new_vip_pick, add_receipt,
    get_pending_receipts, update_receipt_status, get_admin_stats
)
from handlers.content import (
    format_daily_pick, format_vip_pick, format_green_celebration,
    format_receipt_instructions, TERMS_TEXT
)
from handlers.receipt_checker import verify_receipt_with_ai

# Logging
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AccedeGratisBot")

# Estados en memoria para interacción del administrador (difusión o cambio de link)
ADMIN_STATES: dict[int, str] = {}

# ── Teclados Dinámicos de Usuario ────────────────────────────────────────────

async def get_user_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    user = await get_user(user_id)
    pay_url = await get_payment_url()

    if user.get("has_paid_access") == 1:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Ver Siguiente Apuesta VIP", callback_data="view_pick")],
            [InlineKeyboardButton("💬 Soporte VIP", url=SUPPORT_URL)]
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Ver Pronóstico Real de Hoy (Gratis)", callback_data="view_pick")],
        [InlineKeyboardButton(f"💳 Pagar Siguiente Apuesta ({PRICE_EUR})", url=pay_url)],
        [InlineKeyboardButton("🧾 Enviar Justificante de Pago", callback_data="btn_send_receipt")],
        [InlineKeyboardButton("💬 Soporte Oficial", url=SUPPORT_URL)]
    ])

async def get_pick_keyboard(user_id: int) -> InlineKeyboardMarkup:
    user = await get_user(user_id)
    pay_url = await get_payment_url()

    if user.get("has_paid_access") == 1:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Volver al Inicio", callback_data="menu_home")]
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Pagar Siguiente Apuesta ({PRICE_EUR})", url=pay_url)],
        [InlineKeyboardButton("🧾 Enviar Justificante de Pago", callback_data="btn_send_receipt")],
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

# ── Panel de Administración /admintg ─────────────────────────────────────────

async def build_admin_panel():
    stats = await get_admin_stats()
    pay_url = await get_payment_url()
    free_pick = await get_free_pick()
    vip_pick = await get_vip_next_pick()

    text = (
        "🛠️ *PANEL DE CONTROL TIPSTER VIP* (`/admintg`)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 *Estadísticas de Usuarios:*\n"
        f"• 👥 Total usuarios que iniciaron el bot: `{stats['total_users']}`\n"
        f"• 💎 Usuarios con Acceso VIP (Pagados): `{stats['paid_users']}`\n"
        f"• ⏳ Justificantes pendientes de revisar: `{stats['pending_receipts']}`\n"
        f"• ✅ Justificantes aprobados: `{stats['approved_receipts']}`\n\n"
        "🔗 *Enlace de Pago Actual:*\n"
        f"`{pay_url}`\n\n"
        "⚽ *Partido Gratuito del Día:*\n"
        f"• {free_pick.get('match_title', 'No definido')} ({free_pick.get('selection', '')})\n"
        f"• Estado: *{free_pick.get('status', 'PENDIENTE')}*\n\n"
        "👑 *Siguiente Apuesta VIP (De Pago):*\n"
        f"• {vip_pick.get('match_title', 'No definido')} ({vip_pick.get('selection', '')})\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 *Gestión Rápida de Administrador:*"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Marcar VERDE y Notificar Ganador", callback_data="admin_confirm_verde")
        ],
        [
            InlineKeyboardButton("📢 Difusión Masiva", callback_data="admin_ask_broadcast"),
            InlineKeyboardButton("🔗 Modificar Link de Pago", callback_data="admin_change_payurl")
        ],
        [
            InlineKeyboardButton(f"🧾 Justificantes Pendientes ({stats['pending_receipts']})", callback_data="admin_list_receipts"),
            InlineKeyboardButton("📊 Actualizar Panel", callback_data="admin_refresh")
        ],
        [
            InlineKeyboardButton("⚽ Modificar Partido Gratis", callback_data="admin_info_freepick"),
            InlineKeyboardButton("👑 Modificar Partido VIP", callback_data="admin_info_vippick")
        ]
    ])
    return text, keyboard

async def cmd_admintg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    if not await is_admin_user(user.id):
        await update.message.reply_text("⛔ Acceso no autorizado. Este comando es exclusivo del administrador.")
        return

    text, kb = await build_admin_panel()
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# ── Flujo de Comandos de Usuario ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)
    user_db = await get_user(user.id)

    if user_db.get("has_paid_access") == 1:
        welcome_text = (
            f"👑 *¡Hola de nuevo, {user.first_name}! Bienvenido a tu zona VIP.*\n\n"
            "Tienes acceso completo concedido a los pronósticos exclusivos analizados con IA.\n\n"
            "👇 *Pulsa el botón para ver tu siguiente pronóstico VIP:*"
        )
    else:
        welcome_text = (
            f"👋 *¡Hola, {user.first_name}! Bienvenido a Accede Gratis.*\n\n"
            "⚽ *¿Cómo funciona nuestro sistema?*\n"
            "Te facilitamos un **único pronóstico de fútbol 100% REAL de hoy**, seleccionado por Inteligencia Artificial y datos de cuota de valor.\n\n"
            "🎯 *Nuestra política de transparencia:*\n"
            "• El primer pronóstico es **GRATIS** para que compruebes nuestra efectividad con un partido real.\n"
            "• **Si sale VERDE y se acierta**, los siguientes pronósticos exclusivos serán de pago por solo 1.99€ al mes.\n"
            "• Tras pagar, simplemente subes aquí el justificante y el sistema te dará acceso inmediato a la siguiente apuesta.\n\n"
            "👇 *Pulsa abajo para consultar el partido real de hoy:*"
        )

    kb = await get_user_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)
    user_db = await get_user(user.id)

    if user_db.get("has_paid_access") == 1:
        pick = await get_vip_next_pick()
        text = format_vip_pick(pick)
    else:
        pick = await get_free_pick()
        text = format_daily_pick(pick)

    kb = await get_pick_keyboard(user.id)
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pay_url = await get_payment_url()
    text = (
        "💎 *Suscripción Tipster VIP — Máxima Rentabilidad con IA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Accede a los pronósticos de alto valor (+EV) calculados diariamente con modelos estadísticos avanzados:\n\n"
        "✅ *Pronósticos exclusivos analizados a fondo*\n"
        "✅ *Cuotas reales comprobadas en casas oficiales*\n"
        "✅ *Gestión de Stake profesional (1 al 10)*\n"
        "✅ *Alertas inmediatas de oportunidades*\n\n"
        f"💳 *Tarifa Reducida:* `{PRICE_EUR}`\n\n"
        f"👉 [Haz clic aquí para pagar con KunfuPay]({pay_url})\n"
        "Luego envía la captura o foto del comprobante en este chat para activarte al instante."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Pagar con KunfuPay ({PRICE_EUR})", url=pay_url)],
        [InlineKeyboardButton("🧾 Enviar Justificante de Pago", callback_data="btn_send_receipt")],
        [InlineKeyboardButton("🏠 Volver al Inicio", callback_data="menu_home")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_terminos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Volver al Inicio", callback_data="menu_home")]])
    await update.message.reply_text(TERMS_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# ── Activación de VERDE y Difusión Masiva ────────────────────────────────────

async def broadcast_green_to_all(bot) -> tuple[int, int]:
    """Envía la notificación de acierto (VERDE) y link de pago a todos los usuarios."""
    free_pick = await mark_free_pick_won()
    all_users = await get_all_user_ids()
    pay_url = await get_payment_url()

    celebration_text = format_green_celebration(free_pick, pay_url)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Adquirir Siguiente Apuesta ({PRICE_EUR})", url=pay_url)],
        [InlineKeyboardButton("🧾 Ya pagué, enviar justificante", callback_data="btn_send_receipt")]
    ])

    sent = 0
    for uid in all_users:
        try:
            await bot.send_message(chat_id=uid, text=celebration_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass
    return sent, len(all_users)

async def cmd_verde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin_user(user.id):
        await update.message.reply_text("⛔ Solo el administrador puede marcar el partido como VERDE.")
        return

    status_msg = await update.message.reply_text("🚀 Marcando partido gratuito como VERDE y enviando aviso con link de pago a todos los usuarios...")
    sent, total = await broadcast_green_to_all(context.bot)
    await status_msg.edit_text(f"✅ ¡Difusión de VERDE completada! Notificación enviada con éxito a {sent}/{total} usuarios.")

# ── Gestión de Pronósticos y Link de Pago por Comandos ──────────────────────

async def cmd_setpayurl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin_user(user.id):
        return

    new_url = update.message.text.replace("/setpayurl", "").strip()
    if not new_url.startswith("http"):
        await update.message.reply_text("Uso: `/setpayurl https://store.kunfupay.com/...`", parse_mode=ParseMode.MARKDOWN)
        return

    await set_payment_url(new_url)
    await update.message.reply_text(f"✅ Enlace de pago actualizado correctamente a:\n`{new_url}`", parse_mode=ParseMode.MARKDOWN)

async def cmd_nuevo_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin_user(user.id):
        return

    raw = update.message.text.replace("/nuevo_pick", "").replace("/pick", "").strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 7:
        await update.message.reply_text(
            "⚽ *Actualizar Pronóstico Gratuito del Día:*\n"
            "Uso:\n`/pick Partido | Competición | Horario | Selección | Cuota | Stake | Análisis`\n\n"
            "Ejemplo:\n`/pick Getafe CF vs RC Celta | LaLiga EA Sports | Hoy 19:00 | Menos de 2.5 Goles | 1.65 | 1.5 | Partido táctico con baja probabilidad de gol.`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    try:
        await set_new_free_pick(
            match_title=parts[0],
            competition=parts[1],
            match_time=parts[2],
            selection=parts[3],
            odds=float(parts[4]),
            stake=float(parts[5]),
            analysis=parts[6]
        )
        await update.message.reply_text(f"✅ Partido gratuito de hoy actualizado con éxito:\n*{parts[0]}* ({parts[3]} @ {parts[4]})", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error al registrar partido: {e}")

async def cmd_nuevo_vippick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin_user(user.id):
        return

    raw = update.message.text.replace("/vippick", "").strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 7:
        await update.message.reply_text(
            "👑 *Actualizar Siguiente Apuesta VIP:*\n"
            "Uso:\n`/vippick Partido | Competición | Horario | Selección | Cuota | Stake | Análisis`\n\n"
            "Ejemplo:\n`/vippick Real Madrid vs Real Sociedad | LaLiga | Mañana 21:00 | Real Madrid gana + Más de 1.5 | 1.88 | 2.0 | El Madrid promedia 2.3 xG y la Real sufre en transiciones.`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    try:
        await set_new_vip_pick(
            match_title=parts[0],
            competition=parts[1],
            match_time=parts[2],
            selection=parts[3],
            odds=float(parts[4]),
            stake=float(parts[5]),
            analysis=parts[6]
        )
        await update.message.reply_text(f"✅ Siguiente Apuesta VIP guardada con éxito:\n*{parts[0]}* ({parts[3]} @ {parts[4]})", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error al registrar apuesta VIP: {e}")

async def cmd_difusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin_user(user.id):
        return

    msg = update.message.text.replace("/difusion", "").strip()
    if not msg:
        await update.message.reply_text("Uso: `/difusion <Mensaje a transmitir>`", parse_mode=ParseMode.MARKDOWN)
        return

    all_users = await get_all_user_ids()
    pay_url = await get_payment_url()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Acceso VIP ({PRICE_EUR})", url=pay_url)],
        [InlineKeyboardButton("💬 Contactar Soporte", url=SUPPORT_URL)]
    ])

    sent = 0
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=msg, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass
    await update.message.reply_text(f"✅ Difusión enviada a {sent}/{len(all_users)} usuarios.")

# ── Recepción y Verificación de Justificantes de Pago (Fotos) ────────────────

async def photo_receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    if not update.message.photo:
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id

    status_msg = await update.message.reply_text(
        "🤖 *Procesando justificante de pago con Inteligencia Artificial...*\n"
        "Leyendo datos de la imagen (importe, fecha, remitente)...",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        tg_file = await context.bot.get_file(file_id)
        image_bytes = await tg_file.download_as_bytearray()

        # Análisis con Gemini Vision
        ai_verdict = verify_receipt_with_ai(bytes(image_bytes))

        # Registrar en la base de datos
        receipt_id = await add_receipt(
            user_id=user.id,
            username=user.username or user.first_name,
            photo_file_id=file_id,
            ai_analysis=ai_verdict
        )

        await status_msg.edit_text(
            f"🧾 *Justificante Recibido con Éxito (Ref: #{receipt_id})*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 *Diagnóstico Inteligencia Artificial:*\n_{ai_verdict}_\n\n"
            "⏳ *El administrador ha recibido tu comprobante*. En breves minutos se validará tu acceso y podrás ver la **Siguiente Apuesta VIP**.",
            parse_mode=ParseMode.MARKDOWN
        )

        # Notificar a los administradores con foto + botones de aprobación
        admin_ids = await get_admin_user_ids()
        admin_caption = (
            f"🔔 *NUEVO JUSTIFICANTE DE PAGO (ID #{receipt_id})*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Usuario:* {user.first_name} (@{user.username or 'sin_username'} | ID: `{user.id}`)\n"
            f"📅 *Recibido:* Ahora\n\n"
            f"🤖 *Evaluación de Gemini Vision:*\n{ai_verdict}\n\n"
            "¿Deseas validar el justificante y concederle acceso a la siguiente apuesta VIP?"
        )
        admin_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Aprobar Acceso VIP", callback_data=f"rcpt_approve:{receipt_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"rcpt_reject:{receipt_id}")
            ]
        ])

        for aid in admin_ids:
            try:
                await context.bot.send_photo(
                    chat_id=aid,
                    photo=file_id,
                    caption=admin_caption,
                    reply_markup=admin_kb,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error notificando justificante al admin {aid}: {e}")

    except Exception as e:
        logger.error(f"Error procesando justificante de {user.id}: {e}")
        await status_msg.edit_text(
            "⚠️ Hubo un problema al leer la imagen. Por favor, asegúrate de enviar una foto nítida o contacta directamente con soporte.",
            parse_mode=ParseMode.MARKDOWN
        )

# ── Manejador de Mensajes de Texto (Interactivo para Admin) ───────────────────

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_text = update.message.text.strip()
    await upsert_user(user.id, user.username, user.first_name)

    # Comprobar si el administrador está en medio de una acción
    if await is_admin_user(user.id) and user.id in ADMIN_STATES:
        state = ADMIN_STATES.pop(user.id)

        if state == "waiting_broadcast":
            all_users = await get_all_user_ids()
            pay_url = await get_payment_url()
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"💳 Acceso VIP ({PRICE_EUR})", url=pay_url)],
                [InlineKeyboardButton("💬 Soporte Oficial", url=SUPPORT_URL)]
            ])
            sent = 0
            for uid in all_users:
                try:
                    await context.bot.send_message(chat_id=uid, text=user_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
                    sent += 1
                    await asyncio.sleep(0.04)
                except Exception:
                    pass
            await update.message.reply_text(f"✅ Difusión enviada a {sent}/{len(all_users)} usuarios.")
            return

        elif state == "waiting_payurl":
            if user_text.startswith("http"):
                await set_payment_url(user_text)
                await update.message.reply_text(f"✅ Enlace de pago actualizado con éxito a:\n`{user_text}`", parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text("❌ URL no válida. Debe comenzar por http:// o https://")
            return

    # Mensaje normal de usuario: orientar con botones
    kb = await get_user_main_keyboard(user.id)
    await update.message.reply_text(
        "👋 ¡Hola! Utiliza el menú para ver el pronóstico gratuito o enviar tu justificante de pago:",
        reply_markup=kb
    )

# ── Callbacks de Botones ─────────────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    # 1. Menú Principal de Usuario
    if data == "menu_home":
        user_db = await get_user(user.id)
        if user_db.get("has_paid_access") == 1:
            welcome_text = (
                f"👑 *¡Hola, {user.first_name}! Panel VIP.*\n\n"
                "Tu cuenta tiene acceso exclusivo a los pronósticos con IA.\n\n"
                "👇 *Pulsa para ver el pronóstico VIP activo:*"
            )
        else:
            welcome_text = (
                f"👋 *¡Hola, {user.first_name}! Bienvenido a Accede Gratis.*\n\n"
                "⚽ *¿Cómo funciona?*\n"
                "Te facilitamos un **único pronóstico de fútbol 100% REAL de hoy**.\n"
                "• El primer pronóstico es **GRATIS**.\n"
                "• **Si sale VERDE**, la siguiente apuesta exclusiva será de pago (1.99€/mes).\n\n"
                "👇 *Pulsa abajo para consultar el partido real de hoy:*"
            )
        kb = await get_user_main_keyboard(user.id)
        await query.edit_message_text(welcome_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # 2. Ver Pronóstico (Gratis o VIP según estado del usuario)
    elif data == "view_pick":
        user_db = await get_user(user.id)
        if user_db.get("has_paid_access") == 1:
            pick = await get_vip_next_pick()
            text = format_vip_pick(pick)
        else:
            pick = await get_free_pick()
            text = format_daily_pick(pick)
        kb = await get_pick_keyboard(user.id)
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # 3. Instrucciones de Justificante de Pago
    elif data == "btn_send_receipt":
        pay_url = await get_payment_url()
        text = format_receipt_instructions(pay_url)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Pagar con KunfuPay ({PRICE_EUR})", url=pay_url)],
            [InlineKeyboardButton("🏠 Volver al Menú", callback_data="menu_home")]
        ])
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # 4. Administración: Confirmar VERDE
    elif data == "admin_confirm_verde":
        if not await is_admin_user(user.id):
            return
        await query.edit_message_text("🚀 Disparando aviso de VERDE y enlace de pago a todos los usuarios...")
        sent, total = await broadcast_green_to_all(context.bot)
        panel_text, panel_kb = await build_admin_panel()
        await query.message.reply_text(
            f"🎉 *¡ÉXITO! Partido marcado como VERDE.*\nSe ha notificado y enviado el link de pago a {sent}/{total} usuarios.",
            reply_markup=panel_kb,
            parse_mode=ParseMode.MARKDOWN
        )

    # 5. Administración: Iniciar Difusión
    elif data == "admin_ask_broadcast":
        if not await is_admin_user(user.id):
            return
        ADMIN_STATES[user.id] = "waiting_broadcast"
        await query.message.reply_text(
            "✍️ *MODO DIFUSIÓN MASIVA*\n\n"
            "Escribe y envía en este chat el mensaje que deseas enviar a todos los usuarios registrados.\n"
            "_(El mensaje se enviará automáticamente con los botones de pago y soporte)_",
            parse_mode=ParseMode.MARKDOWN
        )

    # 6. Administración: Cambiar Link de Pago
    elif data == "admin_change_payurl":
        if not await is_admin_user(user.id):
            return
        ADMIN_STATES[user.id] = "waiting_payurl"
        pay_url = await get_payment_url()
        await query.message.reply_text(
            f"🔗 *MODIFICAR ENLACE DE PAGO*\n\n"
            f"Enlace actual:\n`{pay_url}`\n\n"
            "Escribe y envía ahora en este chat el nuevo enlace de pago (por ejemplo de KunfuPay):",
            parse_mode=ParseMode.MARKDOWN
        )

    # 7. Administración: Refrescar Panel
    elif data in ("admin_refresh", "admin_stats"):
        if not await is_admin_user(user.id):
            return
        panel_text, panel_kb = await build_admin_panel()
        try:
            await query.edit_message_text(panel_text, reply_markup=panel_kb, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

    # 8. Administración: Listar Justificantes Pendientes
    elif data == "admin_list_receipts":
        if not await is_admin_user(user.id):
            return
        pending = await get_pending_receipts()
        if not pending:
            await query.message.reply_text("✅ No hay justificantes de pago pendientes de revisión.")
            return

        await query.message.reply_text(f"📋 *Hay {len(pending)} justificante(s) pendiente(s):*", parse_mode=ParseMode.MARKDOWN)
        for r in pending[:5]:
            kb_rcpt = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Aprobar Acceso VIP", callback_data=f"rcpt_approve:{r['id']}"),
                    InlineKeyboardButton("❌ Rechazar", callback_data=f"rcpt_reject:{r['id']}")
                ]
            ])
            caption = (
                f"🧾 *Justificante #{r['id']}*\n"
                f"👤 Usuario: @{r['username']} (ID: `{r['user_id']}`)\n"
                f"🤖 Análisis IA:\n{r['ai_analysis']}"
            )
            try:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=r['photo_file_id'],
                    caption=caption,
                    reply_markup=kb_rcpt,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error mostrando justificante #{r['id']}: {e}")

    # 9. Administración: Instrucciones de cambio de pronósticos
    elif data == "admin_info_freepick":
        await query.message.reply_text(
            "⚽ *Para cambiar el partido gratuito de hoy:*\n\n"
            "Envía un mensaje con este formato exacto:\n"
            "`/pick Partido | Competición | Horario | Selección | Cuota | Stake | Análisis`\n\n"
            "Ejemplo:\n"
            "`/pick Getafe CF vs RC Celta | LaLiga | Hoy 19:00 | Menos de 2.5 Goles | 1.65 | 1.5 | Partido muy cerrado.`",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "admin_info_vippick":
        await query.message.reply_text(
            "👑 *Para cambiar la siguiente apuesta VIP:*\n\n"
            "Envía un mensaje con este formato exacto:\n"
            "`/vippick Partido | Competición | Horario | Selección | Cuota | Stake | Análisis`\n\n"
            "Ejemplo:\n"
            "`/vippick Real Madrid vs Real Sociedad | LaLiga | Mañana 21:00 | Gana Real Madrid + Más 1.5 | 1.88 | 2.0 | Excelente valor.`",
            parse_mode=ParseMode.MARKDOWN
        )

    # 10. Aprobación y Rechazo de Justificantes
    elif data.startswith("rcpt_approve:"):
        if not await is_admin_user(user.id):
            return
        receipt_id = int(data.split(":")[1])
        receipt = await update_receipt_status(receipt_id, "APROBADO")
        if receipt:
            try:
                await query.edit_message_caption(
                    caption=(query.message.caption or "") + "\n\n✅ *ESTADO: JUSTIFICANTE APROBADO POR EL ADMIN*",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

            # Notificar al usuario inmediatamente
            target_uid = receipt["user_id"]
            kb_user = InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Ver Siguiente Apuesta VIP", callback_data="view_pick")]
            ])
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=(
                        "🎉 *¡ENHORABUENA! PAGO VERIFICADO CON ÉXITO* 🎉\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        "Tu justificante de pago ha sido revisado y aprobado por el administrador.\n"
                        "¡Ya tienes acceso total a la **Siguiente Apuesta VIP**!\n\n"
                        "👇 *Pulsa el botón para ver el pronóstico exclusivo:*"
                    ),
                    reply_markup=kb_user,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.warning(f"No se pudo notificar al usuario {target_uid}: {e}")

    elif data.startswith("rcpt_reject:"):
        if not await is_admin_user(user.id):
            return
        receipt_id = int(data.split(":")[1])
        receipt = await update_receipt_status(receipt_id, "RECHAZADO")
        if receipt:
            try:
                await query.edit_message_caption(
                    caption=(query.message.caption or "") + "\n\n❌ *ESTADO: JUSTIFICANTE RECHAZADO*",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

            target_uid = receipt["user_id"]
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=(
                        "⚠️ *Aviso sobre tu justificante de pago*\n\n"
                        "El comprobante enviado no ha podido ser validado. "
                        "Por favor, asegúrate de que la captura muestre el importe y la fecha claramente, "
                        "o pulsa en Soporte para recibir asistencia."
                    )
                )
            except Exception:
                pass

# ── Configuración de Comandos en Telegram ────────────────────────────────────

async def setup_commands(app: Application):
    commands = [
        BotCommand("start", "🚀 Inicio y explicación del bot"),
        BotCommand("pronostico", "⚽ Ver pronóstico de hoy"),
        BotCommand("vip", f"⭐ Acceso Siguiente Apuesta VIP ({PRICE_EUR})"),
        BotCommand("terminos", "⚖️ Términos legales del servicio"),
        BotCommand("admintg", "🛠️ Panel de Administrador Tipster"),
    ]
    await app.bot.set_my_commands(commands)
    try:
        await app.bot.set_my_description(
            "Accede Gratis: Pronósticos de Fútbol Reales con Inteligencia Artificial. "
            "Recibe un pronóstico gratuito del día. Si se acierta (VERDE), accede a la siguiente apuesta exclusiva."
        )
        await app.bot.set_my_short_description(
            "Pronósticos de Fútbol Reales con IA & Acceso VIP."
        )
    except Exception as e:
        logger.warning(f"No se pudo actualizar descripción: {e}")
    logger.info("✅ Comandos y descripciones registrados en Telegram")

# ── Construcción y Arranque de la Aplicación ────────────────────────────────

def build_app() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos públicos y de usuario
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("pronostico", cmd_pronostico))
    app.add_handler(CommandHandler("vip", cmd_vip))
    app.add_handler(CommandHandler("terminos", cmd_terminos))

    # Comandos de administración
    app.add_handler(CommandHandler("admintg", cmd_admintg))
    app.add_handler(CommandHandler("verde", cmd_verde))
    app.add_handler(CommandHandler("marcar_verde", cmd_verde))
    app.add_handler(CommandHandler("pick", cmd_nuevo_pick))
    app.add_handler(CommandHandler("nuevo_pick", cmd_nuevo_pick))
    app.add_handler(CommandHandler("vippick", cmd_nuevo_vippick))
    app.add_handler(CommandHandler("nuevo_vippick", cmd_nuevo_vippick))
    app.add_handler(CommandHandler("difusion", cmd_difusion))
    app.add_handler(CommandHandler("setpayurl", cmd_setpayurl))

    # Recepción de fotos (comprobantes de pago)
    app.add_handler(MessageHandler(filters.PHOTO, photo_receipt_handler))

    # Callbacks de botones inline
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Mensajes de texto (interacción de admin o mensajes normales)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    return app

async def main():
    logger.info(f"🚀 Iniciando {BOT_NAME}...")
    await init_db()
    logger.info("✅ Base de datos SQLite inicializada")

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
