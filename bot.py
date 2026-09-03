"""
Bot PDF Ben Informante (@Accedogratis_bot)
Funciones avanzadas de PDF completamente automatizadas.
"""
import os, sys, io, asyncio, logging, tempfile

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, Document
)
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from config import BOT_TOKEN, BOT_NAME, TEMP_DIR, MAX_FILE_MB
from database import init_db, upsert_user, log_operation, get_user_stats, get_all_users
from utils.pdf_engine import (
    extract_text, get_pdf_info, merge_pdfs, split_pdf, split_pdf_all_pages,
    pages_to_zip, rotate_pdf, compress_pdf, protect_pdf, unlock_pdf,
    add_watermark, add_page_numbers, images_to_pdf, text_to_pdf,
    extract_pages, delete_pages
)

# ── Dirs ──────────────────────────────────────────────────────────────────────
os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "data", "bot.log"), encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# ── Estados de conversación ───────────────────────────────────────────────────
(
    WAIT_PDF_SPLIT, WAIT_SPLIT_RANGE,
    WAIT_PDF_ROTATE, WAIT_ROTATE_DEG, WAIT_ROTATE_PAGES,
    WAIT_PDF_PROTECT, WAIT_PROTECT_PASS,
    WAIT_PDF_UNLOCK, WAIT_UNLOCK_PASS,
    WAIT_PDF_WM, WAIT_WM_TEXT,
    WAIT_PDF_EXTRACT, WAIT_EXTRACT_PAGES,
    WAIT_PDF_DELETE, WAIT_DELETE_PAGES,
    WAIT_TEXT_TO_PDF, WAIT_TEXT_TITLE,
    WAIT_MERGE_PDFS,
    WAIT_IMGS_TO_PDF,
) = range(20)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Info PDF",     callback_data="m_info"),
         InlineKeyboardButton("📝 Extraer texto",callback_data="m_text")],
        [InlineKeyboardButton("🔗 Unir PDFs",    callback_data="m_merge"),
         InlineKeyboardButton("✂️ Dividir PDF",  callback_data="m_split")],
        [InlineKeyboardButton("🔄 Rotar páginas",callback_data="m_rotate"),
         InlineKeyboardButton("📦 Comprimir",    callback_data="m_compress")],
        [InlineKeyboardButton("🔒 Proteger",     callback_data="m_protect"),
         InlineKeyboardButton("🔓 Desbloquear",  callback_data="m_unlock")],
        [InlineKeyboardButton("💧 Marca de agua",callback_data="m_watermark"),
         InlineKeyboardButton("🔢 Numerar págs", callback_data="m_pagenums")],
        [InlineKeyboardButton("🖼️ Imágenes→PDF", callback_data="m_img2pdf"),
         InlineKeyboardButton("📋 Texto→PDF",    callback_data="m_text2pdf")],
        [InlineKeyboardButton("📑 Extraer págs", callback_data="m_extract"),
         InlineKeyboardButton("🗑️ Borrar págs",  callback_data="m_delete")],
        [InlineKeyboardButton("📊 Mis estadísticas", callback_data="m_stats"),
         InlineKeyboardButton("❓ Ayuda",         callback_data="m_help")],
    ])

def _main_text(nombre):
    return (
        f"📄 *Ben Informante PDF Bot* — Hola, {nombre}!\n\n"
        "El bot más completo para gestionar tus *archivos PDF*.\n\n"
        "📄 Info · 📝 Extraer texto · 🔗 Unir · ✂️ Dividir\n"
        "🔄 Rotar · 📦 Comprimir · 🔒 Proteger · 🔓 Desbloquear\n"
        "💧 Marca de agua · 🔢 Numerar · 🖼️ Imágenes→PDF\n"
        "📋 Texto→PDF · 📑 Extraer páginas · 🗑️ Borrar páginas\n\n"
        "👇 *Elige una función:*"
    )

def _back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú principal", callback_data="m_back")]])

async def _download_pdf(update_or_msg, context, file_id) -> bytes:
    f = await context.bot.get_file(file_id)
    buf = io.BytesIO()
    await f.download_to_memory(buf)
    return buf.getvalue()

# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)
    await update.effective_message.reply_text(
        _main_text(user.first_name or "👋"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_main_kb()
    )

# ── CALLBACK MENÚ ─────────────────────────────────────────────────────────────

async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    nombre = query.from_user.first_name or "👋"

    instructions = {
        "m_info":     ("📄 *Información del PDF*\n\nEnvíame un archivo PDF y te mostraré\ntodos sus metadatos y estadísticas.", None),
        "m_text":     ("📝 *Extraer texto*\n\nEnvíame un PDF y extraeré todo\nel texto que contenga.", None),
        "m_merge":    ("🔗 *Unir PDFs*\n\nEnvíame los PDFs que quieras unir\n*(uno por uno)* y cuando termines\nescribe `/unir`.", None),
        "m_split":    ("✂️ *Dividir PDF*\n\nEnvíame el PDF y luego indícame\ncómo quieres dividirlo.", None),
        "m_rotate":   ("🔄 *Rotar páginas*\n\nEnvíame el PDF que quieras rotar.", None),
        "m_compress": ("📦 *Comprimir PDF*\n\nEnvíame el PDF y lo comprimiré\npara reducir su tamaño.", None),
        "m_protect":  ("🔒 *Proteger con contraseña*\n\nEnvíame el PDF que quieres proteger.", None),
        "m_unlock":   ("🔓 *Desbloquear PDF*\n\nEnvíame el PDF protegido con contraseña.", None),
        "m_watermark":("💧 *Marca de agua*\n\nEnvíame el PDF donde añadir la marca.", None),
        "m_pagenums": ("🔢 *Numerar páginas*\n\nEnvíame el PDF y añadiré\nlos números de página.", None),
        "m_img2pdf":  ("🖼️ *Imágenes → PDF*\n\nEnvíame las imágenes *(una por una)*\ny cuando termines escribe `/convertir`.", None),
        "m_text2pdf": ("📋 *Texto → PDF*\n\nEscribe o pega el texto que quieres\nconvertir a PDF.", None),
        "m_extract":  ("📑 *Extraer páginas*\n\nEnvíame el PDF del que extraer páginas.", None),
        "m_delete":   ("🗑️ *Borrar páginas*\n\nEnvíame el PDF del que eliminar páginas.", None),
    }

    if action == "m_back":
        await query.edit_message_text(
            _main_text(nombre), parse_mode=ParseMode.MARKDOWN, reply_markup=_main_kb()
        )
    elif action == "m_stats":
        stats = await get_user_stats(query.from_user.id)
        lines = [f"• {k}: *{v}*" for k, v in stats["by_type"].items()]
        text = (
            f"📊 *Tus estadísticas*\n\n"
            f"Total de operaciones: *{stats['total']}*\n\n"
            + ("\n".join(lines) if lines else "_Sin operaciones aún_")
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=_back_kb())
    elif action == "m_help":
        help_text = (
            "📚 *Comandos disponibles*\n\n"
            "`/start` — Menú principal\n"
            "`/info` — Info de un PDF\n"
            "`/texto` — Extraer texto de PDF\n"
            "`/unir` — Unir PDFs (envía varios primero)\n"
            "`/dividir` — Dividir un PDF\n"
            "`/rotar` — Rotar páginas\n"
            "`/comprimir` — Comprimir PDF\n"
            "`/proteger` — Añadir contraseña\n"
            "`/desbloquear` — Quitar contraseña\n"
            "`/marca` — Añadir marca de agua\n"
            "`/numerar` — Añadir números de página\n"
            "`/img2pdf` — Imágenes a PDF\n"
            "`/texto2pdf` — Texto a PDF\n"
            "`/extraer` — Extraer páginas\n"
            "`/borrar` — Borrar páginas\n"
            "`/stats` — Mis estadísticas\n"
            "`/difusion` `<msg>` — Enviar a todos (admin)\n\n"
            "📤 *También puedes enviar un PDF directamente*\nsin comando y el bot te preguntará qué hacer."
        )
        await query.edit_message_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=_back_kb())
    elif action in instructions:
        text, extra_kb = instructions[action]
        kb = extra_kb or _back_kb()
        context.user_data["pending_action"] = action
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        await query.edit_message_text("Usa /start para ver el menú.", reply_markup=_back_kb())

# ── MANEJADOR UNIVERSAL DE PDFs ───────────────────────────────────────────────

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe cualquier PDF y actúa según el contexto pendiente."""
    doc = update.message.document
    user = update.effective_user

    if doc.file_size > MAX_FILE_MB * 1024 * 1024:
        await update.message.reply_text(f"❌ El archivo es demasiado grande (máx {MAX_FILE_MB} MB).")
        return

    await update.message.reply_chat_action("upload_document")
    pdf_bytes = await _download_pdf(update.message, context, doc.file_id)
    pending   = context.user_data.get("pending_action", "")
    fname     = doc.file_name or "documento.pdf"

    # ── INFO ──────────────────────────────────────────────────────────────────
    if pending in ("m_info", "") or not pending:
        info = get_pdf_info(pdf_bytes)
        enc  = "🔒 Sí" if info["encrypted"] else "🔓 No"
        text = (
            f"📄 *Información de: {fname}*\n\n"
            f"📃 Páginas: *{info['pages']}*\n"
            f"💾 Tamaño: *{info['size_kb']} KB*\n"
            f"🔒 Encriptado: *{enc}*\n"
            f"🔤 Palabras aprox.: *{info['words']}*\n\n"
            f"📌 *Metadatos:*\n"
            f"• Título: {info['title']}\n"
            f"• Autor: {info['author']}\n"
            f"• Creador: {info['creator']}\n"
            f"• Asunto: {info['subject']}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Extraer texto", callback_data="do_extract_text"),
             InlineKeyboardButton("📦 Comprimir",     callback_data="do_compress")],
            [InlineKeyboardButton("⬅️ Menú",          callback_data="m_back")],
        ])
        context.user_data["last_pdf"] = pdf_bytes
        context.user_data["last_fname"] = fname
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        await log_operation(user.id, "info", fname)
        context.user_data["pending_action"] = ""

    # ── EXTRAER TEXTO ─────────────────────────────────────────────────────────
    elif pending == "m_text":
        text = extract_text(pdf_bytes)
        if len(text) > 4000:
            # Enviar como archivo de texto
            txt_file = io.BytesIO(text.encode("utf-8"))
            txt_file.name = fname.replace(".pdf", "_texto.txt")
            await update.message.reply_document(
                document=txt_file,
                filename=fname.replace(".pdf", "_texto.txt"),
                caption=f"📝 Texto extraído de *{fname}*\n_{len(text)} caracteres_",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"📝 *Texto de {fname}:*\n\n{text[:3900]}",
                parse_mode=ParseMode.MARKDOWN
            )
        await log_operation(user.id, "extraer_texto", fname)
        context.user_data["pending_action"] = ""

    # ── COMPRIMIR ─────────────────────────────────────────────────────────────
    elif pending == "m_compress":
        compressed = compress_pdf(pdf_bytes)
        orig_kb    = len(pdf_bytes) / 1024
        comp_kb    = len(compressed) / 1024
        saving     = round((1 - comp_kb / orig_kb) * 100, 1) if orig_kb > 0 else 0
        out_file   = io.BytesIO(compressed)
        out_name   = fname.replace(".pdf", "_comprimido.pdf")
        await update.message.reply_document(
            document=out_file, filename=out_name,
            caption=(
                f"📦 *PDF Comprimido*\n\n"
                f"Original: {orig_kb:.1f} KB\n"
                f"Comprimido: {comp_kb:.1f} KB\n"
                f"💚 Ahorro: {saving}%"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        await log_operation(user.id, "comprimir", fname)
        context.user_data["pending_action"] = ""

    # ── NUMERAR PÁGINAS ───────────────────────────────────────────────────────
    elif pending == "m_pagenums":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇️ Abajo centro", callback_data="pn_bottom-center"),
             InlineKeyboardButton("⬇️ Abajo derecha", callback_data="pn_bottom-right")],
            [InlineKeyboardButton("⬆️ Arriba centro", callback_data="pn_top-center")],
        ])
        context.user_data["last_pdf"]   = pdf_bytes
        context.user_data["last_fname"] = fname
        await update.message.reply_text(
            "🔢 ¿Dónde quieres los números de página?",
            reply_markup=kb
        )
        await log_operation(user.id, "numerar", fname)
        context.user_data["pending_action"] = ""

    # ── MARCA DE AGUA — guardar PDF y pedir texto ─────────────────────────────
    elif pending == "m_watermark":
        context.user_data["last_pdf"]   = pdf_bytes
        context.user_data["last_fname"] = fname
        await update.message.reply_text(
            "💧 ¿Qué texto quieres como marca de agua?\n"
            "Ejemplo: `CONFIDENCIAL` o `BORRADOR`",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["pending_action"] = "wm_waiting_text"

    # ── PROTEGER — guardar PDF y pedir contraseña ─────────────────────────────
    elif pending == "m_protect":
        context.user_data["last_pdf"]   = pdf_bytes
        context.user_data["last_fname"] = fname
        await update.message.reply_text("🔒 ¿Qué contraseña quieres usar para proteger el PDF?")
        context.user_data["pending_action"] = "protect_waiting_pass"

    # ── DESBLOQUEAR — guardar PDF y pedir contraseña ──────────────────────────
    elif pending == "m_unlock":
        context.user_data["last_pdf"]   = pdf_bytes
        context.user_data["last_fname"] = fname
        await update.message.reply_text("🔓 Escribe la contraseña del PDF para desbloquearlo:")
        context.user_data["pending_action"] = "unlock_waiting_pass"

    # ── ROTAR — guardar PDF y pedir grados ────────────────────────────────────
    elif pending == "m_rotate":
        context.user_data["last_pdf"]   = pdf_bytes
        context.user_data["last_fname"] = fname
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ 90° izquierda",  callback_data="rot_270"),
             InlineKeyboardButton("↪️ 90° derecha",    callback_data="rot_90")],
            [InlineKeyboardButton("🔁 180°",            callback_data="rot_180")],
        ])
        await update.message.reply_text(
            "🔄 ¿Cuánto quieres rotar todas las páginas?",
            reply_markup=kb
        )
        context.user_data["pending_action"] = ""

    # ── DIVIDIR — guardar PDF y pedir rango ───────────────────────────────────
    elif pending == "m_split":
        context.user_data["last_pdf"]   = pdf_bytes
        context.user_data["last_fname"] = fname
        info  = get_pdf_info(pdf_bytes)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Una página por archivo (ZIP)", callback_data="split_all")],
            [InlineKeyboardButton("✏️ Indicar rangos manualmente",   callback_data="split_custom")],
        ])
        await update.message.reply_text(
            f"✂️ *Dividir PDF* — {info['pages']} páginas\n\n¿Cómo quieres dividirlo?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
        context.user_data["pending_action"] = ""

    # ── EXTRAER PÁGINAS ───────────────────────────────────────────────────────
    elif pending == "m_extract":
        context.user_data["last_pdf"]   = pdf_bytes
        context.user_data["last_fname"] = fname
        info = get_pdf_info(pdf_bytes)
        await update.message.reply_text(
            f"📑 *Extraer páginas* — {info['pages']} páginas\n\n"
            "Indica las páginas que quieres extraer:\n"
            "Ejemplo: `1,3,5` o `2-6`",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["pending_action"] = "extract_waiting_pages"

    # ── BORRAR PÁGINAS ────────────────────────────────────────────────────────
    elif pending == "m_delete":
        context.user_data["last_pdf"]   = pdf_bytes
        context.user_data["last_fname"] = fname
        info = get_pdf_info(pdf_bytes)
        await update.message.reply_text(
            f"🗑️ *Borrar páginas* — {info['pages']} páginas\n\n"
            "Indica las páginas que quieres eliminar:\n"
            "Ejemplo: `1,3,5` o `2-6`",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["pending_action"] = "delete_waiting_pages"

    # ── UNIR — acumular PDFs ──────────────────────────────────────────────────
    elif pending == "m_merge":
        if "merge_list" not in context.user_data:
            context.user_data["merge_list"]   = []
            context.user_data["merge_names"]  = []
        context.user_data["merge_list"].append(pdf_bytes)
        context.user_data["merge_names"].append(fname)
        n = len(context.user_data["merge_list"])
        await update.message.reply_text(
            f"✅ PDF {n} añadido: *{fname}*\n\n"
            f"Envía otro PDF o escribe `/unir` para unirlos todos.",
            parse_mode=ParseMode.MARKDOWN
        )

    # ── SIN CONTEXTO — preguntar qué hacer ───────────────────────────────────
    else:
        info = get_pdf_info(pdf_bytes)
        context.user_data["last_pdf"]   = pdf_bytes
        context.user_data["last_fname"] = fname
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Ver info",      callback_data="do_info"),
             InlineKeyboardButton("📝 Extraer texto", callback_data="do_text")],
            [InlineKeyboardButton("📦 Comprimir",     callback_data="do_compress"),
             InlineKeyboardButton("🔄 Rotar",         callback_data="do_rotate")],
            [InlineKeyboardButton("🔒 Proteger",      callback_data="do_protect"),
             InlineKeyboardButton("💧 Marca agua",    callback_data="do_watermark")],
            [InlineKeyboardButton("✂️ Dividir",       callback_data="do_split"),
             InlineKeyboardButton("🔢 Numerar págs",  callback_data="do_pagenums")],
        ])
        await update.message.reply_text(
            f"📄 PDF recibido: *{fname}*\n_{info['pages']} páginas · {info['size_kb']} KB_\n\n¿Qué quieres hacer?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )

# ── MANEJADOR DE TEXTO (contraseñas, marcas, etc.) ───────────────────────────

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe texto según el estado pendiente."""
    text  = update.message.text
    user  = update.effective_user
    state = context.user_data.get("pending_action", "")
    pdf   = context.user_data.get("last_pdf")
    fname = context.user_data.get("last_fname", "documento.pdf")

    if not pdf and state not in ("m_text2pdf", "waiting_text2pdf"):
        await update.message.reply_text("⚠️ Envíame primero un archivo PDF.")
        return

    # ── MARCA DE AGUA ─────────────────────────────────────────────────────────
    if state == "wm_waiting_text":
        await update.message.reply_chat_action("upload_document")
        result = add_watermark(pdf, text)
        out    = io.BytesIO(result)
        out_name = fname.replace(".pdf", "_marca.pdf")
        await update.message.reply_document(
            document=out, filename=out_name,
            caption=f"💧 Marca de agua *«{text}»* añadida.", parse_mode=ParseMode.MARKDOWN
        )
        await log_operation(user.id, "marca_agua", fname)
        context.user_data["pending_action"] = ""

    # ── PROTEGER ──────────────────────────────────────────────────────────────
    elif state == "protect_waiting_pass":
        await update.message.reply_chat_action("upload_document")
        result = protect_pdf(pdf, text)
        out    = io.BytesIO(result)
        out_name = fname.replace(".pdf", "_protegido.pdf")
        await update.message.reply_document(
            document=out, filename=out_name,
            caption=f"🔒 PDF protegido con contraseña.", parse_mode=ParseMode.MARKDOWN
        )
        await log_operation(user.id, "proteger", fname)
        context.user_data["pending_action"] = ""

    # ── DESBLOQUEAR ───────────────────────────────────────────────────────────
    elif state == "unlock_waiting_pass":
        await update.message.reply_chat_action("upload_document")
        result = unlock_pdf(pdf, text)
        if result is None:
            await update.message.reply_text("❌ Contraseña incorrecta. Inténtalo de nuevo:")
            return
        out  = io.BytesIO(result)
        out_name = fname.replace(".pdf", "_desbloqueado.pdf")
        await update.message.reply_document(
            document=out, filename=out_name,
            caption="🔓 PDF desbloqueado correctamente."
        )
        await log_operation(user.id, "desbloquear", fname)
        context.user_data["pending_action"] = ""

    # ── RANGO DE DIVISIÓN ─────────────────────────────────────────────────────
    elif state == "split_custom_waiting":
        await update.message.reply_chat_action("upload_document")
        pages_dict = split_pdf(pdf, text)
        if len(pages_dict) == 1:
            name, data = next(iter(pages_dict.items()))
            await update.message.reply_document(document=io.BytesIO(data), filename=name,
                                                 caption="✂️ PDF dividido.")
        else:
            zip_bytes = pages_to_zip(pages_dict)
            await update.message.reply_document(
                document=io.BytesIO(zip_bytes), filename="division.zip",
                caption=f"✂️ {len(pages_dict)} archivos divididos en ZIP."
            )
        await log_operation(user.id, "dividir", fname)
        context.user_data["pending_action"] = ""

    # ── EXTRAER PÁGINAS ───────────────────────────────────────────────────────
    elif state == "extract_waiting_pages":
        try:
            nums = []
            for part in text.replace(" ", "").split(","):
                if "-" in part:
                    a, b = part.split("-")
                    nums.extend(range(int(a), int(b) + 1))
                else:
                    nums.append(int(part))
            result = extract_pages(pdf, nums)
            out_name = fname.replace(".pdf", f"_paginas.pdf")
            await update.message.reply_document(
                document=io.BytesIO(result), filename=out_name,
                caption=f"📑 Páginas {text} extraídas."
            )
            await log_operation(user.id, "extraer_paginas", fname)
        except Exception:
            await update.message.reply_text("❌ Formato incorrecto. Usa: `1,3,5` o `2-6`", parse_mode=ParseMode.MARKDOWN)
        context.user_data["pending_action"] = ""

    # ── BORRAR PÁGINAS ────────────────────────────────────────────────────────
    elif state == "delete_waiting_pages":
        try:
            nums = []
            for part in text.replace(" ", "").split(","):
                if "-" in part:
                    a, b = part.split("-")
                    nums.extend(range(int(a), int(b) + 1))
                else:
                    nums.append(int(part))
            result = delete_pages(pdf, nums)
            out_name = fname.replace(".pdf", f"_editado.pdf")
            await update.message.reply_document(
                document=io.BytesIO(result), filename=out_name,
                caption=f"🗑️ Páginas {text} eliminadas."
            )
            await log_operation(user.id, "borrar_paginas", fname)
        except Exception:
            await update.message.reply_text("❌ Formato incorrecto. Usa: `1,3,5` o `2-6`", parse_mode=ParseMode.MARKDOWN)
        context.user_data["pending_action"] = ""

    # ── TEXTO → PDF ───────────────────────────────────────────────────────────
    elif state == "waiting_text2pdf_title":
        context.user_data["text2pdf_title"] = text
        await update.message.reply_text("📋 Ahora escribe o pega el texto que quieres convertir a PDF:")
        context.user_data["pending_action"] = "waiting_text2pdf_body"

    elif state == "waiting_text2pdf_body":
        title = context.user_data.get("text2pdf_title", "Documento")
        result = text_to_pdf(text, title)
        await update.message.reply_chat_action("upload_document")
        await update.message.reply_document(
            document=io.BytesIO(result), filename=f"{title[:30]}.pdf",
            caption=f"📋 *{title}* convertido a PDF.", parse_mode=ParseMode.MARKDOWN
        )
        await log_operation(user.id, "texto_a_pdf", title)
        context.user_data["pending_action"] = ""

# ── CALLBACKS DE ACCIÓN RÁPIDA ────────────────────────────────────────────────

async def callback_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    pdf    = context.user_data.get("last_pdf")
    fname  = context.user_data.get("last_fname", "documento.pdf")
    user   = query.from_user

    if not pdf and not action.startswith("pn_") and not action.startswith("rot_") and not action.startswith("split_"):
        await query.edit_message_text("⚠️ Envíame primero un PDF.")
        return

    # Info
    if action == "do_info":
        info = get_pdf_info(pdf)
        enc  = "🔒 Sí" if info["encrypted"] else "🔓 No"
        await query.edit_message_text(
            f"📄 *Info: {fname}*\n\n📃 Páginas: *{info['pages']}*\n"
            f"💾 Tamaño: *{info['size_kb']} KB*\n🔒 Encriptado: *{enc}*\n"
            f"🔤 Palabras: *{info['words']}*\n\n"
            f"Título: {info['title']}\nAutor: {info['author']}",
            parse_mode=ParseMode.MARKDOWN, reply_markup=_back_kb()
        )

    # Extraer texto
    elif action in ("do_extract_text", "do_text"):
        text = extract_text(pdf)
        if len(text) > 3800:
            txt_file = io.BytesIO(text.encode("utf-8"))
            await query.message.reply_document(document=txt_file, filename=fname.replace(".pdf", ".txt"),
                                                caption="📝 Texto extraído.")
        else:
            await query.edit_message_text(f"📝 *Texto:*\n\n{text[:3800]}", parse_mode=ParseMode.MARKDOWN,
                                           reply_markup=_back_kb())
        await log_operation(user.id, "extraer_texto", fname)

    # Comprimir
    elif action in ("do_compress",):
        await query.message.reply_chat_action("upload_document")
        compressed = compress_pdf(pdf)
        orig_kb = len(pdf) / 1024
        comp_kb = len(compressed) / 1024
        saving  = round((1 - comp_kb / orig_kb) * 100, 1)
        await query.message.reply_document(
            document=io.BytesIO(compressed),
            filename=fname.replace(".pdf", "_comprimido.pdf"),
            caption=f"📦 Comprimido: {orig_kb:.0f}→{comp_kb:.0f} KB (💚 {saving}% menos)"
        )
        await log_operation(user.id, "comprimir", fname)
        await query.edit_message_text("✅ PDF comprimido enviado.", reply_markup=_back_kb())

    # Rotar
    elif action.startswith("rot_"):
        deg = int(action.split("_")[1])
        await query.message.reply_chat_action("upload_document")
        result = rotate_pdf(pdf, deg)
        await query.message.reply_document(
            document=io.BytesIO(result), filename=fname.replace(".pdf", f"_rotado{deg}.pdf"),
            caption=f"🔄 PDF rotado {deg}°."
        )
        await log_operation(user.id, f"rotar_{deg}", fname)
        await query.edit_message_text("✅ PDF rotado enviado.", reply_markup=_back_kb())

    # Numerar páginas
    elif action.startswith("pn_"):
        pos = action.replace("pn_", "")
        await query.message.reply_chat_action("upload_document")
        result = add_page_numbers(pdf, pos)
        await query.message.reply_document(
            document=io.BytesIO(result), filename=fname.replace(".pdf", "_numerado.pdf"),
            caption="🔢 Páginas numeradas."
        )
        await log_operation(user.id, "numerar_paginas", fname)
        await query.edit_message_text("✅ PDF con números de página enviado.", reply_markup=_back_kb())

    # Dividir — todas las páginas
    elif action == "split_all":
        await query.message.reply_chat_action("upload_document")
        pages_dict = split_pdf_all_pages(pdf)
        zip_bytes  = pages_to_zip(pages_dict)
        await query.message.reply_document(
            document=io.BytesIO(zip_bytes), filename=f"{fname.replace('.pdf','')}_paginas.zip",
            caption=f"✂️ {len(pages_dict)} páginas separadas en ZIP."
        )
        await log_operation(user.id, "dividir_todo", fname)
        await query.edit_message_text("✅ ZIP enviado.", reply_markup=_back_kb())

    # Dividir — rango personalizado
    elif action == "split_custom":
        await query.edit_message_text(
            "✂️ Escribe los rangos de páginas:\n\n"
            "Ejemplos:\n"
            "• `1-3` → páginas 1 a 3\n"
            "• `1-3,5,7-9` → varios rangos",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["pending_action"] = "split_custom_waiting"

    # Acciones que cambian pending_action
    elif action == "do_rotate":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ 90° izquierda", callback_data="rot_270"),
             InlineKeyboardButton("↪️ 90° derecha",   callback_data="rot_90")],
            [InlineKeyboardButton("🔁 180°",           callback_data="rot_180")],
        ])
        await query.edit_message_text("🔄 ¿Cuánto quieres rotar?", reply_markup=kb)

    elif action == "do_protect":
        await query.edit_message_text("🔒 Escribe la contraseña que quieres usar:")
        context.user_data["pending_action"] = "protect_waiting_pass"

    elif action == "do_watermark":
        await query.edit_message_text(
            "💧 ¿Qué texto de marca de agua?\nEjemplo: `CONFIDENCIAL`",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["pending_action"] = "wm_waiting_text"

    elif action == "do_split":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Una página por archivo (ZIP)", callback_data="split_all")],
            [InlineKeyboardButton("✏️ Indicar rangos manualmente",   callback_data="split_custom")],
        ])
        await query.edit_message_text("✂️ ¿Cómo quieres dividir el PDF?", reply_markup=kb)

    elif action == "do_pagenums":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇️ Abajo centro",  callback_data="pn_bottom-center"),
             InlineKeyboardButton("⬇️ Abajo derecha", callback_data="pn_bottom-right")],
            [InlineKeyboardButton("⬆️ Arriba centro", callback_data="pn_top-center")],
        ])
        await query.edit_message_text("🔢 ¿Dónde quieres los números de página?", reply_markup=kb)

# ── COMANDOS ESPECÍFICOS ──────────────────────────────────────────────────────

async def cmd_unir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    merge_list  = context.user_data.get("merge_list", [])
    merge_names = context.user_data.get("merge_names", [])
    if len(merge_list) < 2:
        await update.message.reply_text("⚠️ Necesito al menos 2 PDFs. Envíalos antes de escribir /unir.")
        return
    await update.message.reply_chat_action("upload_document")
    result = merge_pdfs(merge_list)
    await update.message.reply_document(
        document=io.BytesIO(result), filename="union.pdf",
        caption=f"🔗 *{len(merge_list)} PDFs unidos*\n\n" + "\n".join(f"• {n}" for n in merge_names),
        parse_mode=ParseMode.MARKDOWN
    )
    await log_operation(update.effective_user.id, "unir", f"{len(merge_list)} archivos")
    context.user_data.pop("merge_list", None)
    context.user_data.pop("merge_names", None)

async def cmd_texto2pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 ¿Cuál será el título del documento?")
    context.user_data["pending_action"] = "waiting_text2pdf_title"

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await get_user_stats(update.effective_user.id)
    lines = [f"• {k}: *{v}*" for k, v in stats["by_type"].items()]
    await update.message.reply_text(
        f"📊 *Tus estadísticas*\n\nTotal: *{stats['total']}*\n\n" + ("\n".join(lines) or "_Sin operaciones_"),
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_difusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /difusion <mensaje>")
        return
    msg   = " ".join(context.args)
    users = await get_all_users()
    sent = failed = 0
    await update.message.reply_text(f"📢 Enviando a {len(users)} usuarios...")
    for u in users:
        try:
            await context.bot.send_message(u["user_id"], f"📢 *Mensaje:*\n\n{msg}", parse_mode=ParseMode.MARKDOWN)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"✅ Enviado: {sent} | ❌ Fallidos: {failed}")

async def cmd_img2pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pending_action"] = "m_img2pdf"
    context.user_data["img_list"] = []
    await update.message.reply_text("🖼️ Envíame las imágenes una por una y luego escribe `/convertir`.")

async def cmd_convertir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    img_list = context.user_data.get("img_list", [])
    if not img_list:
        await update.message.reply_text("⚠️ Envíame imágenes antes de /convertir.")
        return
    await update.message.reply_chat_action("upload_document")
    result = images_to_pdf(img_list)
    await update.message.reply_document(
        document=io.BytesIO(result), filename="imagenes.pdf",
        caption=f"🖼️ *{len(img_list)} imágenes* convertidas a PDF.", parse_mode=ParseMode.MARKDOWN
    )
    await log_operation(update.effective_user.id, "img_a_pdf", f"{len(img_list)} imágenes")
    context.user_data.pop("img_list", None)

# ── MANEJADOR DE IMÁGENES ─────────────────────────────────────────────────────

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("pending_action", "")
    if state == "m_img2pdf":
        photo = update.message.photo[-1] if update.message.photo else None
        if photo:
            f   = await context.bot.get_file(photo.file_id)
            buf = io.BytesIO()
            await f.download_to_memory(buf)
            if "img_list" not in context.user_data:
                context.user_data["img_list"] = []
            context.user_data["img_list"].append(buf.getvalue())
            n = len(context.user_data["img_list"])
            await update.message.reply_text(f"✅ Imagen {n} añadida. Envía más o escribe `/convertir`.")
    else:
        await update.message.reply_text("💡 Para convertir imágenes a PDF escribe primero `/img2pdf`.")

# ── CONSTRUCCIÓN DE LA APP ────────────────────────────────────────────────────

def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("menu",      cmd_start))
    app.add_handler(CommandHandler("unir",      cmd_unir))
    app.add_handler(CommandHandler("texto2pdf", cmd_texto2pdf))
    app.add_handler(CommandHandler("stats",     cmd_stats))
    app.add_handler(CommandHandler("difusion",  cmd_difusion))
    app.add_handler(CommandHandler("img2pdf",   cmd_img2pdf))
    app.add_handler(CommandHandler("convertir", cmd_convertir))

    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_menu,   pattern=r"^m_"))
    app.add_handler(CallbackQueryHandler(callback_action, pattern=r"^(do_|rot_|pn_|split_)"))

    # Archivos PDF
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    # Imágenes
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    # Texto (contraseñas, marcas, etc.)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    app.add_error_handler(lambda u, c: logger.error(f"Error: {c.error}"))
    return app


async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start",     "🏠 Menú principal"),
        BotCommand("unir",      "🔗 Unir PDFs enviados"),
        BotCommand("texto2pdf", "📋 Convertir texto a PDF"),
        BotCommand("img2pdf",   "🖼️ Convertir imágenes a PDF"),
        BotCommand("convertir", "✅ Finalizar conversión imágenes"),
        BotCommand("stats",     "📊 Mis estadísticas"),
        BotCommand("difusion",  "📢 Enviar mensaje a todos"),
    ])


async def health_server():
    """Servidor HTTP mínimo para el health-check de Render."""
    from aiohttp import web
    port = int(os.environ.get("PORT", 8080))
    async def handle(_req):
        return web.Response(text="OK — Ben Informante PDF Bot activo ✅")
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info(f"🌐 Health server en puerto {port}")


async def main():
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "temp"), exist_ok=True)
    await init_db()
    logger.info("✅ Base de datos inicializada")

    # Health check para Render
    try:
        await health_server()
    except Exception as e:
        logger.warning(f"⚠️ Health server no disponible: {e}")

    app = build_app()
    await app.initialize()
    await set_commands(app)
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

    logger.info("🟢 Ben Informante PDF Bot activo!")
    logger.info("👉 Abre @Accedogratis_bot en Telegram para probarlo")

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot detenido")
