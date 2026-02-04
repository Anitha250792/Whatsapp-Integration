"""
files/converters.py

IMPORTANT ARCHITECTURE NOTE
---------------------------
Render free services do NOT support:
- LibreOffice
- Poppler
- OCR / heavy CPU jobs

Therefore:
- DOCX → PDF
- PDF → DOCX

are intentionally DISABLED in web requests.

These functions are designed for:
✔ Celery workers
✔ Background jobs
✔ Dedicated conversion microservice

This keeps the API stable and avoids 500 errors.
"""

import os
import io

from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


# =====================================================
# 🔁 WORD → PDF (ASYNC ONLY)
# =====================================================
def word_to_pdf(docx_path, output_path):
    """
    DOCX → PDF conversion

    ❌ Disabled on web
    ✅ Intended for Celery

    Example:
        word_to_pdf.delay(docx_path, output_path)
    """
    raise RuntimeError(
        "Word to PDF conversion runs asynchronously (background worker)"
    )


# =====================================================
# 🔁 PDF → WORD (ASYNC ONLY)
# =====================================================
def pdf_to_word(pdf_path, output_path):
    """
    PDF → DOCX conversion

    ❌ Disabled on web
    ✅ Intended for Celery
    """
    raise RuntimeError(
        "PDF to Word conversion runs asynchronously (background worker)"
    )


# =====================================================
# ✍ SIGN PDF (SAFE)
# =====================================================
def sign_pdf(pdf_path, output_path, signer="Signed User"):
    """
    PDF signing is heavy and unsafe on Render web dynos.
    Must be processed asynchronously (Celery worker).
    """
    raise RuntimeError("PDF signing is processed asynchronously")



# =====================================================
# ➕ MERGE PDFs (SAFE)
# =====================================================
def merge_pdfs(pdf_paths, output_path):
    merger = PdfMerger()
    for path in pdf_paths:
        merger.append(path)
    merger.write(output_path)
    merger.close()
    return output_path


# =====================================================
# ✂ SPLIT PDF (SAFE)
# =====================================================
def split_pdf(pdf_path, output_dir):
    reader = PdfReader(pdf_path)
    output_files = []

    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        out_path = os.path.join(output_dir, f"page_{i + 1}.pdf")
        with open(out_path, "wb") as f:
            writer.write(f)

        output_files.append(out_path)

    return output_files
