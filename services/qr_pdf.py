"""Create print-ready PDF documents containing DocInBox access QR codes."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import fitz
import qrcode


_PAGE_WIDTH = 612  # US Letter, in points.
_PAGE_HEIGHT = 792
_QR_COLOR = (0.07, 0.10, 0.16)
_TEXT_COLOR = (0.12, 0.16, 0.23)
_MUTED_COLOR = (0.38, 0.43, 0.51)


def generate_qr_pdf(public_url: str, output_path: str | Path) -> Path:
    """Create a one-page, print-ready PDF containing the active public QR code."""
    url = str(public_url).strip()
    if not url:
        raise ValueError("No hay una dirección pública para generar el código QR.")
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("La dirección del código QR debe ser una URL HTTPS válida.")

    destination = Path(output_path).expanduser().resolve()
    if destination.suffix.lower() != ".pdf":
        raise ValueError("El archivo de salida debe tener extensión .pdf.")
    destination.parent.mkdir(parents=True, exist_ok=True)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=1,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()

    document = fitz.open()
    temporary_path = destination.with_name(f".{destination.stem}.tmp.pdf")
    try:
        if temporary_path.exists():
            temporary_path.unlink()

        page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        page.draw_rect(page.rect, color=None, fill=(1, 1, 1), overlay=False)

        title = "DocInBox"
        title_width = fitz.get_text_length(title, fontname="hebo", fontsize=27)
        page.insert_text(
            ((_PAGE_WIDTH - title_width) / 2, 76),
            title,
            fontname="hebo",
            fontsize=27,
            color=_TEXT_COLOR,
        )

        subtitle = "Escanea el codigo QR para abrir el formulario de recepcion"
        subtitle_width = fitz.get_text_length(subtitle, fontname="helv", fontsize=11)
        page.insert_text(
            ((_PAGE_WIDTH - subtitle_width) / 2, 110),
            subtitle,
            fontname="helv",
            fontsize=11,
            color=_MUTED_COLOR,
        )

        qr_size = 360.0
        qr_left = (_PAGE_WIDTH - qr_size) / 2
        qr_top = 145.0
        module_size = qr_size / len(matrix)
        shape = page.new_shape()
        for row_index, row in enumerate(matrix):
            for column_index, is_dark in enumerate(row):
                if not is_dark:
                    continue
                left = qr_left + column_index * module_size
                top = qr_top + row_index * module_size
                shape.draw_rect(
                    fitz.Rect(
                        left,
                        top,
                        left + module_size + 0.03,
                        top + module_size + 0.03,
                    )
                )
        shape.finish(color=None, fill=_QR_COLOR, closePath=True)
        shape.commit(overlay=True)

        prompt = "Abre la camara de tu dispositivo y apunta al codigo QR."
        prompt_width = fitz.get_text_length(prompt, fontname="helv", fontsize=10)
        page.insert_text(
            ((_PAGE_WIDTH - prompt_width) / 2, 545),
            prompt,
            fontname="helv",
            fontsize=10,
            color=_TEXT_COLOR,
        )

        url_box = fitz.Rect(54, 575, _PAGE_WIDTH - 54, 665)
        remaining = -1.0
        for font_size in (9.5, 9, 8.5, 8, 7.5):
            remaining = page.insert_textbox(
                url_box,
                url,
                fontname="cour",
                fontsize=font_size,
                lineheight=1.25,
                color=_TEXT_COLOR,
                align=1,
            )
            if remaining >= 0:
                break
        if remaining < 0:
            raise ValueError("La dirección es demasiado larga para incluirla en el PDF.")

        footer = "Acceso publico de DocInBox"
        footer_width = fitz.get_text_length(footer, fontname="helv", fontsize=8)
        page.insert_text(
            ((_PAGE_WIDTH - footer_width) / 2, 746),
            footer,
            fontname="helv",
            fontsize=8,
            color=_MUTED_COLOR,
        )

        document.set_metadata(
            {
                "title": "Codigo QR de acceso - DocInBox",
                "author": "DocInBox",
                "subject": "Codigo QR para abrir el formulario de recepcion",
            }
        )
        document.save(str(temporary_path), garbage=4, deflate=True)
    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()
        raise
    finally:
        document.close()

    temporary_path.replace(destination)
    return destination
