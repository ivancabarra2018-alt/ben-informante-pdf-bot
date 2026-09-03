"""
Motor de operaciones PDF — todas las funciones sin dependencias externas pesadas.
Usa pypdf (puro Python) + reportlab + Pillow.
"""
import io
import os
import zipfile
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import cm
from PIL import Image


# ─────────────────────────────────────────────────────────────────────────────
# 1. EXTRAER TEXTO
# ─────────────────────────────────────────────────────────────────────────────

def extract_text(pdf_bytes: bytes) -> str:
    """Extrae todo el texto de un PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            pages_text.append(f"── Página {i} ──\n{text.strip()}")
    return "\n\n".join(pages_text) if pages_text else "⚠️ No se encontró texto extraíble (puede ser un PDF escaneado)."


# ─────────────────────────────────────────────────────────────────────────────
# 2. INFO / METADATOS
# ─────────────────────────────────────────────────────────────────────────────

def get_pdf_info(pdf_bytes: bytes) -> dict:
    """Devuelve metadatos y estadísticas del PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    meta = reader.metadata or {}
    pages = len(reader.pages)
    encrypted = reader.is_encrypted
    size_kb = len(pdf_bytes) / 1024
    # Contar palabras aproximadas
    full_text = " ".join(p.extract_text() or "" for p in reader.pages)
    words = len(full_text.split())
    return {
        "pages": pages,
        "encrypted": encrypted,
        "size_kb": round(size_kb, 1),
        "words": words,
        "title": meta.get("/Title", "—"),
        "author": meta.get("/Author", "—"),
        "creator": meta.get("/Creator", "—"),
        "producer": meta.get("/Producer", "—"),
        "subject": meta.get("/Subject", "—"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. UNIR PDFs
# ─────────────────────────────────────────────────────────────────────────────

def merge_pdfs(pdf_bytes_list: list[bytes]) -> bytes:
    """Une múltiples PDFs en uno."""
    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 4. DIVIDIR PDF
# ─────────────────────────────────────────────────────────────────────────────

def split_pdf(pdf_bytes: bytes, ranges: str) -> dict[str, bytes]:
    """
    Divide el PDF según rangos. ranges='1-3,5,7-9'
    Devuelve dict {nombre: bytes}
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total = len(reader.pages)
    result = {}

    parts = [p.strip() for p in ranges.split(",")]
    for part in parts:
        if "-" in part:
            a, b = part.split("-")
            start, end = int(a) - 1, int(b) - 1
        else:
            start = end = int(part) - 1

        start = max(0, min(start, total - 1))
        end   = max(0, min(end,   total - 1))

        writer = PdfWriter()
        for i in range(start, end + 1):
            writer.add_page(reader.pages[i])

        out = io.BytesIO()
        writer.write(out)
        label = f"paginas_{start+1}-{end+1}.pdf"
        result[label] = out.getvalue()

    return result


def split_pdf_all_pages(pdf_bytes: bytes) -> dict[str, bytes]:
    """Divide cada página en un archivo separado → ZIP."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    result = {}
    for i, page in enumerate(reader.pages, 1):
        writer = PdfWriter()
        writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        result[f"pagina_{i:03d}.pdf"] = out.getvalue()
    return result


def pages_to_zip(pages_dict: dict[str, bytes]) -> bytes:
    """Empaqueta un dict de nombre→bytes en un ZIP."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in pages_dict.items():
            zf.writestr(name, data)
    return zip_buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 5. ROTAR PÁGINAS
# ─────────────────────────────────────────────────────────────────────────────

def rotate_pdf(pdf_bytes: bytes, degrees: int, pages: str = "all") -> bytes:
    """Rota páginas del PDF. pages='all' o '1,3,5'"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    total = len(reader.pages)

    if pages == "all":
        target = set(range(total))
    else:
        target = set()
        for p in pages.split(","):
            p = p.strip()
            if p.isdigit():
                target.add(int(p) - 1)

    for i, page in enumerate(reader.pages):
        if i in target:
            page.rotate(degrees)
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 6. COMPRIMIR PDF
# ─────────────────────────────────────────────────────────────────────────────

def compress_pdf(pdf_bytes: bytes) -> bytes:
    """Comprime el PDF eliminando contenido redundante."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)
    writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 7. PROTEGER / DESPROTEGER
# ─────────────────────────────────────────────────────────────────────────────

def protect_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """Añade contraseña al PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password, algorithm="AES-256")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def unlock_pdf(pdf_bytes: bytes, password: str) -> Optional[bytes]:
    """Elimina la contraseña del PDF. Devuelve None si la contraseña es incorrecta."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if reader.is_encrypted:
        result = reader.decrypt(password)
        if result == 0:
            return None  # Contraseña incorrecta
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 8. MARCA DE AGUA (WATERMARK)
# ─────────────────────────────────────────────────────────────────────────────

def add_watermark(pdf_bytes: bytes, text: str, opacity: float = 0.3) -> bytes:
    """Añade marca de agua de texto a todas las páginas."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color

    # Crear página de marca de agua
    wm_buf = io.BytesIO()
    c = canvas.Canvas(wm_buf, pagesize=A4)
    w, h = A4
    c.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
    c.setFont("Helvetica-Bold", 48)
    c.saveState()
    c.translate(w / 2, h / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.save()
    wm_bytes = wm_buf.getvalue()

    wm_reader = PdfReader(io.BytesIO(wm_bytes))
    wm_page   = wm_reader.pages[0]

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(wm_page)
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 9. NUMERAR PÁGINAS
# ─────────────────────────────────────────────────────────────────────────────

def add_page_numbers(pdf_bytes: bytes, position: str = "bottom-center") -> bytes:
    """Añade números de página al PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    total  = len(reader.pages)

    for i, page in enumerate(reader.pages, 1):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        num_buf = io.BytesIO()
        c = canvas.Canvas(num_buf, pagesize=(w, h))
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.3, 0.3, 0.3)

        text = f"Página {i} de {total}"
        if position == "bottom-center":
            c.drawCentredString(w / 2, 20, text)
        elif position == "bottom-right":
            c.drawRightString(w - 20, 20, text)
        elif position == "top-center":
            c.drawCentredString(w / 2, h - 20, text)
        c.save()

        num_reader = PdfReader(io.BytesIO(num_buf.getvalue()))
        page.merge_page(num_reader.pages[0])
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 10. IMÁGENES → PDF
# ─────────────────────────────────────────────────────────────────────────────

def images_to_pdf(image_bytes_list: list[bytes]) -> bytes:
    """Convierte una o varias imágenes a PDF."""
    imgs = []
    for img_bytes in image_bytes_list:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        imgs.append(img)

    out = io.BytesIO()
    if imgs:
        imgs[0].save(out, format="PDF", save_all=True, append_images=imgs[1:])
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 11. PDF → IMÁGENES (primera página con Pillow)
# ─────────────────────────────────────────────────────────────────────────────

def pdf_first_page_preview(pdf_bytes: bytes) -> Optional[bytes]:
    """Genera una preview de la primera página del PDF como imagen PNG."""
    try:
        # Intentar con pdf2image si está disponible
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=150)
        if images:
            buf = io.BytesIO()
            images[0].save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 12. CREAR PDF DESDE TEXTO
# ─────────────────────────────────────────────────────────────────────────────

def text_to_pdf(text: str, title: str = "Documento") -> bytes:
    """Convierte texto plano a PDF con formato."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.setFillColorRGB(0.1, 0.1, 0.5)
    c.drawString(2 * cm, h - 2 * cm, title)

    # Línea separadora
    c.setStrokeColorRGB(0.1, 0.1, 0.5)
    c.line(2 * cm, h - 2.3 * cm, w - 2 * cm, h - 2.3 * cm)

    # Contenido
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0, 0, 0)
    y = h - 3 * cm
    line_h = 0.55 * cm
    max_w  = int((w - 4 * cm) / (0.28 * cm))  # chars por línea aprox

    for raw_line in text.split("\n"):
        # Wrap manual
        while len(raw_line) > max_w:
            c.drawString(2 * cm, y, raw_line[:max_w])
            raw_line = raw_line[max_w:]
            y -= line_h
            if y < 2 * cm:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = h - 2 * cm
        c.drawString(2 * cm, y, raw_line)
        y -= line_h
        if y < 2 * cm:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = h - 2 * cm

    c.save()
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 13. EXTRAER PÁGINAS ESPECÍFICAS
# ─────────────────────────────────────────────────────────────────────────────

def extract_pages(pdf_bytes: bytes, page_nums: list[int]) -> bytes:
    """Extrae páginas específicas (1-indexed) y devuelve un nuevo PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    total  = len(reader.pages)
    for n in page_nums:
        if 1 <= n <= total:
            writer.add_page(reader.pages[n - 1])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 14. ELIMINAR PÁGINAS
# ─────────────────────────────────────────────────────────────────────────────

def delete_pages(pdf_bytes: bytes, page_nums: list[int]) -> bytes:
    """Elimina páginas específicas (1-indexed)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    to_del = set(page_nums)
    for i, page in enumerate(reader.pages, 1):
        if i not in to_del:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
