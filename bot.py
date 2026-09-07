"""
🤖 Accede Gratis | Pronósticos Deportivos & IA (@Accedogratis_bot)
Bot tipster profesional con pronóstico real de fútbol, panel secreto /admintg,
verificación de justificantes de pago con IA (Gemini Vision), reseteo de acceso (7.99€)
y sistema de compensación si se falla el pronóstico.
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
    BOT_TOKEN, BOT_NAME, PRICE_EUR,
    SUPPORT_USER, SUPPORT_URL
)
from database import (
    init_db, upsert_user, get_user, is_admin_user, get_admin_user_ids,
    get_all_users, get_all_user_ids, get_payment_url, set_payment_url,
    get_free_pick, get_next_paid_pick, mark_free_pick_won,
    mark_pick_lost_and_compensate_all, mark_user_viewed_free_pick,
    mark_user_viewed_paid_pick, set_new_free_pick, set_new_paid_pick,
    add_receipt, get_pending_receipts, approve_receipt_and_reset_user,
    reject_receipt, get_admin_stats
)
from handlers.content import (
    format_daily_pick, format_paid_pick, format_exhausted_free_pick,
    format_green_celebration, format_red_compensation,
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

    # Si tiene acceso activo pagado
    if user.get("has_paid_access") == 1:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Ver Siguiente Pronóstico", callback_data="view_pick")],
            [InlineKeyboardButton("💬 Soporte Oficial", url=SUPPORT_URL)]
        ])

    # Si ya consumió su pronóstico gratuito y no ha pagado
    if user.get("has_seen_free_pick") == 1:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Desbloquear Siguiente ({PRICE_EUR})", url=pay_url)],
            [InlineKeyboardButton("🧾 Enviar Justificante de Pago", callback_data="btn_send_receipt")],
            [InlineKeyboardButton("💬 Soporte Oficial", url=SUPPORT_URL)]
        ])

    # Usuario nuevo (aún no ha visto su pronóstico gratis)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Ver Pronóstico Gratuito de Hoy", callback_data="view_pick")],
        [InlineKeyboardButton(f"💳 Siguiente Pronóstico ({PRICE_EUR})", url=pay_url)],
        [InlineKeyboardButton("🧾 Ya pagué (Enviar Justificante)", callback_data="btn_send_receipt")],
        [InlineKeyboardButton("💬 Soporte Oficial", url=SUPPORT_URL)]
    ])

async def get_pick_keyboard(user_id: int) -> InlineKeyboardMarkup:
    pay_url = await get_payment_url()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Adquirir Siguiente ({PRICE_EUR})", url=pay_url)],
        [InlineKeyboardButton("🧾 Enviar Justificante", callback_data="btn_send_receipt")],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
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

# ── Panel de Administración Oculto (/admintg) ────────────────────────────────

async def build_admin_panel():
    stats = await get_admin_stats()
    pay_url = await get_payment_url()
    free_pick = await get_free_pick()
    paid_pick = await get_next_paid_pick()

    text = (
        "🛠️ *PANEL DE CONTROL TIPSTER PRO* (`/admintg`)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 *Estadísticas de Usuarios:*\n"
        f"• 👥 Total usuarios registrados: `{stats['total_users']}`\n"
        f"• 💳 Usuarios con Acceso Activo: `{stats['paid_users']}`\n"
        f"• ⏳ Justificantes pendientes de revisar: `{stats['pending_receipts']}`\n"
        f"• ✅ Justificantes aprobados (reseteados): `{stats['approved_receipts']}`\n\n"
        "🔗 *Enlace de Pago KunfuPay:*\n"
        f"`{pay_url}`\n\n"
        "⚽ *Partido Gratuito Hoy:*\n"
        f"• {free_pick.get('match_title', 'Sin definir')} ({free_pick.get('selection', '')})\n"
        f"• Estado: *{free_pick.get('status', 'PENDIENTE')}*\n\n"
        f"👑 *Siguiente Pronóstico ({PRICE_EUR}):*\n"
        f"• {paid_pick.get('match_title', 'Sin definir')} ({paid_pick.get('selection', '')})\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 *Acciones de Administrador:*"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Marcar VERDE (Notificar Ganador)", callback_data="admin_confirm_verde")
        ],
        [
            InlineKeyboardButton("🔴 Marcar ROJO (Resetear Todos Gratis)", callback_data="admin_confirm_rojo")
        ],
        [
            InlineKeyboardButton("📢 Difusión Masiva", callback_data="admin_ask_broadcast"),
            InlineKeyboardButton("🔗 Cambiar Link Pago", callback_data="admin_change_payurl")
        ],
        [
            InlineKeyboardButton(f"🧾 Justificantes ({stats['pending_receipts']})", callback_data="admin_list_receipts"),
            InlineKeyboardButton("🔄 Refrescar Panel", callback_data="admin_refresh")
        ],
        [
            InlineKeyboardButton("⚽ Modificar Partido Gratis", callback_data="admin_info_freepick"),
            InlineKeyboardButton("👑 Modificar Partido Siguiente", callback_data="admin_info_paidpick")
        ]
    ])
    return text, keyboard

async def cmd_admintg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    if not await is_admin_user(user.id):
        await update.message.reply_text("⛔ Comando no disponible.")
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
            f"👑 *¡Hola de nuevo, {user.first_name}! Acceso Activo.*\n\n"
            "Tu bot está reseteado con acceso al **Siguiente Pronóstico** con IA.\n\n"
            "👇 *Pulsa el botón para ver el pronóstico exclusivo:*"
        )
    elif user_db.get("has_seen_free_pick") == 1:
        pay_url = await get_payment_url()
        welcome_text = format_exhausted_free_pick(pay_url)
    else:
        welcome_text = (
            f"👋 *¡Hola, {user.first_name}! Bienvenido a Accede Gratis.*\n\n"
            "⚽ *¿Cómo funciona nuestro sistema?*\n"
            "Te facilitamos un **único pronóstico de fútbol 100% REAL de hoy**, analizado con Inteligencia Artificial y datos de cuota de valor.\n\n"
            "🎯 *Política de transparencia total:*\n"
            "• El primer pronóstico es **100% GRATIS** para que compruebes nuestra efectividad con un partido real.\n"
            f"• **Si sale VERDE y se acierta**, el Siguiente Pronóstico exclusivo costará solo **{PRICE_EUR}**.\n"
            "• Quien pague sube el comprobante aquí, su bot se **resetea** y verá el de mañana / siguiente.\n"
            "• **Si se falla el pronóstico**, se resetea automáticamente a todos los usuarios para que el siguiente día lo reciban **GRATIS** sin pagar.\n\n"
            "👇 *Pulsa abajo para consultar el partido real de hoy:*"
        )

    kb = await get_user_main_keyboard(user.id)
    await update.message.reply_text(welcome_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)
    user_db = await get_user(user.id)

    # 1. Si tiene acceso pagado activo
    if user_db.get("has_paid_access") == 1:
        pick = await get_next_paid_pick()
        text = format_paid_pick(pick)
        await mark_user_viewed_paid_pick(user.id)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]])
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # 2. Si ya consumió el gratis y no ha pagado
    if user_db.get("has_seen_free_pick") == 1:
        pay_url = await get_payment_url()
        text = format_exhausted_free_pick(pay_url)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Pagar Siguiente Pronóstico ({PRICE_EUR})", url=pay_url)],
            [InlineKeyboardButton("🧾 Enviar Justificante de Pago", callback_data="btn_send_receipt")],
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
        ])
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # 3. Usuario que aún no ha visto su pronóstico gratuito
    pick = await get_free_pick()
    text = format_daily_pick(pick)
    await mark_user_viewed_free_pick(user.id)
    kb = await get_pick_keyboard(user.id)
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_siguiente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pay_url = await get_payment_url()
    text = (
        f"🎯 *Siguiente Pronóstico de Fútbol con IA ({PRICE_EUR})*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Adquiere el siguiente pronóstico analizado matemáticamente con valor esperado (+EV):\n\n"
        "✅ *Partido real seleccionado por algoritmos de IA*\n"
        "✅ *Cuotas reales comprobadas en casas de apuestas*\n"
        "✅ *Stake recomendado y análisis detallado*\n\n"
        f"💳 *Precio:* `{PRICE_EUR}` (pago único)\n\n"
        f"👉 [Haz clic aquí para pagar en KunfuPay]({pay_url})\n\n"
        "Una vez realizado el pago, envía la captura del justificante en este chat para **resetear tu bot** y acceder de inmediato."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Pagar con KunfuPay ({PRICE_EUR})", url=pay_url)],
        [InlineKeyboardButton("🧾 Enviar Justificante de Pago", callback_data="btn_send_receipt")],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def cmd_terminos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Volver al Inicio", callback_data="menu_home")]])
    await update.message.reply_text(TERMS_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# ── Activación de VERDE / ROJO y Difusión Masiva ────────────────────────────

async def broadcast_green_to_all(bot) -> tuple[int, int]:
    """Marca VERDE y envía celebración + venta del siguiente a todos los usuarios."""
    free_pick = await mark_free_pick_won()
    all_users = await get_all_user_ids()
    pay_url = await get_payment_url()

    celebration_text = format_green_celebration(free_pick, pay_url)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Comprar Siguiente Pronóstico ({PRICE_EUR})", url=pay_url)],
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

async def broadcast_red_to_all(bot) -> tuple[int, int]:
    """Marca ROJO, resetea a todos los usuarios y avisa de la compensación gratuita."""
    pick, total_reset = await mark_pick_lost_and_compensate_all()
    all_users = await get_all_user_ids()

    red_text = format_red_compensation(pick)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Ver Pronóstico Gratuito Mañana", callback_data="view_pick")],
        [InlineKeyboardButton("💬 Soporte Oficial", url=SUPPORT_URL)]
    ])

    sent = 0
    for uid in all_users:
        try:
            await bot.send_message(chat_id=uid, text=red_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass
    return sent, total_reset

async def cmd_verde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin_user(user.id):
        return

    status_msg = await update.message.reply_text("🚀 Marcando partido como VERDE y lanzando difusión a todos los usuarios...")
    sent, total = await broadcast_green_to_all(context.bot)
    await status_msg.edit_text(f"✅ ¡Difusión de VERDE entregada a {sent}/{total} usuarios con éxito!")

async def cmd_rojo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin_user(user.id):
        return

    status_msg = await update.message.reply_text("🔴 Marcando pronóstico como FALLADO (ROJO), reseteando bot a todos los usuarios y notificando compensación...")
    sent, total_reset = await broadcast_red_to_all(context.bot)
    await status_msg.edit_text(f"🛡️ ¡Compensación completada! Se ha reseteado el bot a {total_reset} usuarios y se notificó a {sent} usuarios.")

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
            "Ejemplo:\n`/pick Francia vs Italia | UEFA Nations League | Hoy 20:45 | Ambos Equipos Marcan | 1.78 | 2.0 | Partido estelar en París con alta expectativa goleadora.`",
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

async def cmd_nuevo_paidpick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin_user(user.id):
        return

    raw = update.message.text.replace("/paidpick", "").replace("/vippick", "").strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 7:
        await update.message.reply_text(
            f"👑 *Actualizar Siguiente Pronóstico de Pago ({PRICE_EUR}):*\n"
            "Uso:\n`/paidpick Partido | Competición | Horario | Selección | Cuota | Stake | Análisis`\n\n"
            "Ejemplo:\n`/paidpick Suiza vs España | UEFA Nations League | Próxima Jornada 20:45 | España gana o empate + Más 1.5 | 1.82 | 2.5 | La campeona de Europa llega invicta y con alta efectividad.`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    try:
        await set_new_paid_pick(
            match_title=parts[0],
            competition=parts[1],
            match_time=parts[2],
            selection=parts[3],
            odds=float(parts[4]),
            stake=float(parts[5]),
            analysis=parts[6]
        )
        await update.message.reply_text(f"✅ Siguiente Pronóstico ({PRICE_EUR}) guardado con éxito:\n*{parts[0]}* ({parts[3]} @ {parts[4]})", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error al registrar pronóstico: {e}")

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
        [InlineKeyboardButton(f"💳 Siguiente Pronóstico ({PRICE_EUR})", url=pay_url)],
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
        "Verificando comprobante legítimo de pago...",
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
            "⏳ *El administrador ha recibido tu comprobante*. En breves instantes será validado y **tu bot quedará reseteado** para ver el siguiente pronóstico.",
            parse_mode=ParseMode.MARKDOWN
        )

        # Notificar a los administradores con foto + botones de aprobación
        admin_ids = await get_admin_user_ids()
        admin_caption = (
            f"🔔 *NUEVO JUSTIFICANTE DE PAGO (ID #{receipt_id})*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Usuario:* {user.first_name} (@{user.username or 'sin_username'} | ID: `{user.id}`)\n"
            f"💰 *Producto:* Siguiente Pronóstico ({PRICE_EUR})\n\n"
            f"🤖 *Evaluación de Gemini Vision:*\n{ai_verdict}\n\n"
            "¿Deseas validar el justificante y resetear el bot a este usuario?"
        )
        admin_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Aprobar y Resetear Bot", callback_data=f"rcpt_approve:{receipt_id}"),
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
            "⚠️ Hubo un problema al procesar la imagen. Por favor, asegúrate de enviar una foto nítida o contacta directamente con soporte.",
            parse_mode=ParseMode.MARKDOWN
        )

# ── Manejador de Mensajes de Texto (Interactivo para Admin) ───────────────────

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_text = update.message.text.strip()
    await upsert_user(user.id, user.username, user.first_name)

    # Comprobar si el administrador está en medio de una acción interactiva
    if await is_admin_user(user.id) and user.id in ADMIN_STATES:
        state = ADMIN_STATES.pop(user.id)

        if state == "waiting_broadcast":
            all_users = await get_all_user_ids()
            pay_url = await get_payment_url()
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"💳 Siguiente Pronóstico ({PRICE_EUR})", url=pay_url)],
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
        "👋 ¡Hola! Utiliza el menú para consultar pronósticos o enviar tu justificante de pago:",
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
                f"👑 *¡Hola, {user.first_name}! Acceso Activo.*\n\n"
                "Tu bot está reseteado con acceso al **Siguiente Pronóstico** con IA.\n\n"
                "👇 *Pulsa para ver el pronóstico activo:*"
            )
        elif user_db.get("has_seen_free_pick") == 1:
            pay_url = await get_payment_url()
            welcome_text = format_exhausted_free_pick(pay_url)
        else:
            welcome_text = (
                f"👋 *¡Hola, {user.first_name}! Bienvenido a Accede Gratis.*\n\n"
                "⚽ *¿Cómo funciona?*\n"
                "Te facilitamos un **único pronóstico de fútbol 100% REAL de hoy**.\n"
                "• El primer pronóstico es **GRATIS**.\n"
                f"• **Si sale VERDE**, el siguiente será de pago ({PRICE_EUR}).\n"
                "• **Si se falla**, se resetea gratis para que mañana lo recibas sin pagar nada.\n\n"
                "👇 *Pulsa abajo para consultar el partido real de hoy:*"
            )
        kb = await get_user_main_keyboard(user.id)
        await query.edit_message_text(welcome_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # 2. Ver Pronóstico (Gratis o Pagado con control de agotamiento)
    elif data == "view_pick":
        user_db = await get_user(user.id)

        # Si pagó y tiene acceso activo: ve el pronóstico de pago y consume ese ciclo
        if user_db.get("has_paid_access") == 1:
            pick = await get_next_paid_pick()
            text = format_paid_pick(pick)
            await mark_user_viewed_paid_pick(user.id)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]])
            await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            return

        # Si ya consumió el gratis y no ha pagado: bloquear
        if user_db.get("has_seen_free_pick") == 1:
            pay_url = await get_payment_url()
            text = format_exhausted_free_pick(pay_url)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"💳 Pagar Siguiente Pronóstico ({PRICE_EUR})", url=pay_url)],
                [InlineKeyboardButton("🧾 Enviar Justificante de Pago", callback_data="btn_send_receipt")],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_home")]
            ])
            await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            return

        # Si es su primera vez gratuita: muestra y marca como visto
        pick = await get_free_pick()
        text = format_daily_pick(pick)
        await mark_user_viewed_free_pick(user.id)
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
        await query.edit_message_text("🚀 Disparando aviso de VERDE y oferta del siguiente pronóstico a todos los usuarios...")
        sent, total = await broadcast_green_to_all(context.bot)
        panel_text, panel_kb = await build_admin_panel()
        await query.message.reply_text(
            f"🎉 *¡ÉXITO! Partido marcado como VERDE.*\nSe ha notificado y ofrecido el siguiente pronóstico a {sent}/{total} usuarios.",
            reply_markup=panel_kb,
            parse_mode=ParseMode.MARKDOWN
        )

    # 5. Administración: Confirmar ROJO y Compensar
    elif data == "admin_confirm_rojo":
        if not await is_admin_user(user.id):
            return
        await query.edit_message_text("🔴 Marcando pronóstico como FALLADO, reseteando a todos los usuarios y enviando compensación...")
        sent, total_reset = await broadcast_red_to_all(context.bot)
        panel_text, panel_kb = await build_admin_panel()
        await query.message.reply_text(
            f"🛡️ *¡COMPENSACIÓN COMPLETADA!*\n• Partido marcado como FALLADO.\n• Se ha reseteado el bot a {total_reset} usuarios.\n• Notificación de regalo enviada a {sent} usuarios.",
            reply_markup=panel_kb,
            parse_mode=ParseMode.MARKDOWN
        )

    # 6. Administración: Iniciar Difusión
    elif data == "admin_ask_broadcast":
        if not await is_admin_user(user.id):
            return
        ADMIN_STATES[user.id] = "waiting_broadcast"
        await query.message.reply_text(
            "✍️ *MODO DIFUSIÓN MASIVA*\n\n"
            "Escribe y envía en este chat el mensaje que deseas enviar a todos los usuarios registrados.\n"
            f"_(Se adjuntarán los botones automáticos de compra de {PRICE_EUR} y soporte)_",
            parse_mode=ParseMode.MARKDOWN
        )

    # 7. Administración: Cambiar Link de Pago
    elif data == "admin_change_payurl":
        if not await is_admin_user(user.id):
            return
        ADMIN_STATES[user.id] = "waiting_payurl"
        pay_url = await get_payment_url()
        await query.message.reply_text(
            f"🔗 *MODIFICAR ENLACE DE PAGO*\n\n"
            f"Enlace actual:\n`{pay_url}`\n\n"
            "Escribe y envía ahora en este chat el nuevo enlace de pago de KunfuPay:",
            parse_mode=ParseMode.MARKDOWN
        )

    # 8. Administración: Refrescar Panel
    elif data == "admin_refresh":
        if not await is_admin_user(user.id):
            return
        panel_text, panel_kb = await build_admin_panel()
        try:
            await query.edit_message_text(panel_text, reply_markup=panel_kb, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

    # 9. Administración: Listar Justificantes Pendientes
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
                    InlineKeyboardButton("✅ Aprobar y Resetear Bot", callback_data=f"rcpt_approve:{r['id']}"),
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

    # 10. Administración: Ayuda de sintaxis de pronósticos
    elif data == "admin_info_freepick":
        await query.message.reply_text(
            "⚽ *Actualizar Partido Gratuito:*\n"
            "`/pick Partido | Competición | Horario | Selección | Cuota | Stake | Análisis`\n\n"
            "Ejemplo:\n"
            "`/pick Francia vs Italia | UEFA Nations League | Hoy 20:45 | Ambos Equipos Marcan | 1.78 | 2.0 | Cruce en París con alto promedio ofensivo.`",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "admin_info_paidpick":
        await query.message.reply_text(
            f"👑 *Actualizar Siguiente Pronóstico ({PRICE_EUR}):*\n"
            "`/paidpick Partido | Competición | Horario | Selección | Cuota | Stake | Análisis`\n\n"
            "Ejemplo:\n"
            "`/paidpick Suiza vs España | UEFA Nations League | Próxima Jornada 20:45 | España gana o empate + Más 1.5 | 1.82 | 2.5 | La campeona de Europa mantiene un rendimiento sólido.`",
            parse_mode=ParseMode.MARKDOWN
        )

    # 11. Aprobación y Rechazo de Justificantes (con Reseteo de Bot)
    elif data.startswith("rcpt_approve:"):
        if not await is_admin_user(user.id):
            return
        receipt_id = int(data.split(":")[1])
        receipt = await approve_receipt_and_reset_user(receipt_id)
        if receipt:
            try:
                await query.edit_message_caption(
                    caption=(query.message.caption or "") + "\n\n✅ *ESTADO: APROBADO Y BOT RESETEADO*",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

            target_uid = receipt["user_id"]
            kb_user = InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Ver Siguiente Pronóstico", callback_data="view_pick")]
            ])
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=(
                        f"🎉 *¡PAGO DE {PRICE_EUR} VERIFICADO CON ÉXITO!* 🎉\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        "Tu justificante ha sido validado y **tu bot se ha reseteado**.\n"
                        "Ya tienes acceso exclusivo al **Siguiente Pronóstico**.\n\n"
                        "👇 *Pulsa el botón para ver el pronóstico completo:*"
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
        receipt = await reject_receipt(receipt_id)
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
                        "Por favor, envía una captura clara donde se observe el pago o contacta a soporte para asistencia."
                    )
                )
            except Exception:
                pass

# ── Configuración de Comandos en Telegram (SOLO COMANDOS PÚBLICOS) ───────────

async def setup_commands(app: Application):
    """
    IMPORTANTE: El menú /admintg y comandos de admin están COMPLETAMENTE OCULTOS.
    No se registran en set_my_commands para que nadie más pueda verlos en el autocompletado.
    """
    commands = [
        BotCommand("start", "🚀 Iniciar bot y consultar pronóstico"),
        BotCommand("pronostico", "⚽ Ver pronóstico de fútbol"),
        BotCommand("siguiente", f"🎯 Adquirir Siguiente Pronóstico ({PRICE_EUR})"),
        BotCommand("terminos", "⚖️ Términos legales del servicio"),
    ]
    await app.bot.set_my_commands(commands)
    try:
        await app.bot.set_my_description(
            "Accede Gratis: Pronósticos de Fútbol Reales con Inteligencia Artificial. "
            "Recibe un pronóstico gratuito del día. Si se acierta (VERDE), accede al siguiente. Si se falla, recibes compensación gratuita."
        )
        await app.bot.set_my_short_description(
            "Pronósticos de Fútbol Reales con IA."
        )
    except Exception as e:
        logger.warning(f"No se pudo actualizar descripción: {e}")
    logger.info("✅ Comandos públicos registrados en Telegram (Comandos admin ocultos)")

# ── Construcción y Arranque de la Aplicación ────────────────────────────────

def build_app() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos públicos y de usuario
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("pronostico", cmd_pronostico))
    app.add_handler(CommandHandler("siguiente", cmd_siguiente))
    app.add_handler(CommandHandler("vip", cmd_siguiente))  # Redirección por compatibilidad
    app.add_handler(CommandHandler("terminos", cmd_terminos))

    # Comandos de administración (TOTALMENTE OCULTOS)
    app.add_handler(CommandHandler("admintg", cmd_admintg))
    app.add_handler(CommandHandler("verde", cmd_verde))
    app.add_handler(CommandHandler("marcar_verde", cmd_verde))
    app.add_handler(CommandHandler("rojo", cmd_rojo))
    app.add_handler(CommandHandler("marcar_rojo", cmd_rojo))
    app.add_handler(CommandHandler("pick", cmd_nuevo_pick))
    app.add_handler(CommandHandler("nuevo_pick", cmd_nuevo_pick))
    app.add_handler(CommandHandler("paidpick", cmd_nuevo_paidpick))
    app.add_handler(CommandHandler("vippick", cmd_nuevo_paidpick))
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
    logger.info("✅ Base de datos SQLite lista con partidos reales y reglas de reseteo")

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
