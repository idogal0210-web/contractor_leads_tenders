"""
processors/ocr.py — חילוץ טקסט מ-PDF ומסמכים סרוקים (חינמי).

שילוב pdfplumber למסמכים דיגיטליים ו-pytesseract לסריקות.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Union

import structlog

log = structlog.get_logger(__name__)


class OCRMethod(str, Enum):
    PDFPLUMBER = "pdfplumber"
    TESSERACT = "tesseract"
    NONE = "none"


@dataclass
class OCRResult:
    text: str
    method: OCRMethod
    page_count: int
    confidence: float  # 0.0-1.0
    error: str | None = None


def extract_text_from_string(content: str) -> OCRResult:
    """החזרת טקסט שכבר קיים במלואו כתוצאת OCR ישירה."""
    return OCRResult(
        text=content,
        method=OCRMethod.NONE,
        page_count=1,
        confidence=1.0,
        error=None,
    )


def extract_text_from_pdf(pdf_source: Union[str, Path, bytes]) -> OCRResult:
    """
    חילוץ חכם של טקסט מקובץ PDF:
    1. ניסיון חילוץ טקסט ישיר עם pdfplumber (מהיר, חינמי ומדויק).
    2. אם הטקסט הממוצע לעמוד קטן מ-100 תווים (סביר שמדובר במסמך סרוק) — מעבר ל-Tesseract OCR.
    """
    extracted_text_parts: list[str] = []
    page_count = 0
    pdf_stream = io.BytesIO(pdf_source) if isinstance(pdf_source, bytes) else pdf_source

    # 1. בדיקת pdfplumber
    try:
        import pdfplumber

        with pdfplumber.open(pdf_stream) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    extracted_text_parts.append(txt.strip())

        full_text = "\n\n".join(extracted_text_parts)
        # אם יש מספיק טקסט
        if page_count > 0 and len(full_text) / page_count >= 80:
            log.info("pdfplumber_success", pages=page_count, chars=len(full_text))
            return OCRResult(
                text=full_text,
                method=OCRMethod.PDFPLUMBER,
                page_count=page_count,
                confidence=0.95,
            )

        log.info("pdf_sparse_text_falling_back_to_ocr", pages=page_count, chars=len(full_text))

    except ImportError:
        log.warning("pdfplumber_not_installed")
    except Exception as exc:
        log.warning("pdfplumber_failed", error=str(exc))

    # 2. מעבר ל-pytesseract אם pdfplumber החזיר מעט מדי טקסט
    try:
        import pytesseract
        from PIL import Image

        # במידה וזה stream צריך לפתוח מחדש
        if isinstance(pdf_source, bytes):
            pdf_stream = io.BytesIO(pdf_source)

        ocr_pages: list[str] = []
        try:
            from pdf2image import convert_from_bytes, convert_from_path
            if isinstance(pdf_source, bytes):
                images = convert_from_bytes(pdf_source)
            else:
                images = convert_from_path(str(pdf_source))

            page_count = len(images)
            for img in images:
                txt = pytesseract.image_to_string(img, lang="heb+eng")
                if txt.strip():
                    ocr_pages.append(txt.strip())

            full_ocr_text = "\n\n".join(ocr_pages)
            return OCRResult(
                text=full_ocr_text,
                method=OCRMethod.TESSERACT,
                page_count=page_count,
                confidence=0.75,
            )
        except Exception as ocr_err:
            log.warning("pdf2image_or_tesseract_failed", error=str(ocr_err))
            # אם יש לפחות את הטקסט החלקי של pdfplumber, נחזיר אותו
            if extracted_text_parts:
                return OCRResult(
                    text="\n\n".join(extracted_text_parts),
                    method=OCRMethod.PDFPLUMBER,
                    page_count=page_count,
                    confidence=0.50,
                )
            return OCRResult(
                text="",
                method=OCRMethod.TESSERACT,
                page_count=page_count,
                confidence=0.0,
                error=str(ocr_err),
            )

    except ImportError:
        log.warning("pytesseract_not_installed")
        return OCRResult(
            text="\n\n".join(extracted_text_parts),
            method=OCRMethod.PDFPLUMBER,
            page_count=page_count,
            confidence=0.50 if extracted_text_parts else 0.0,
            error="pytesseract not installed",
        )
