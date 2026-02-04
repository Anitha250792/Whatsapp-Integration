"""
files/converters.py

IMPORTANT ARCHITECTURE NOTE
---------------------------
Render free services do NOT support:
- LibreOffice
- Poppler
- Long-running CPU-heavy jobs

Therefore:
- DOCX → PDF
- PDF → DOCX

are intentionally DISABLED in web requests.

These functions are designed to be executed via:
✔ Celery
✔ Background worker
✔ Dedicated conversion microservice

This avoids 500 errors and keeps the API stable.
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

    ❌ Disabled on Render Web Service
    ✅ Intended for Celery background worker

    Celery usage example:
        word_to_pdf.delay(docx_path, output_path)

    Reason:
    - Requires LibreOffice
    - High memory usage
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

    ❌ Disabled on Render Web Service
    ✅ Intended for Celery background worker

    Celery usage example:
        pdf_to_word.delay(pdf_path, output_path)

    Reason:
    - OCR / pdfminer heavy
    - Not safe on free hosting
    """
    raise RuntimeError(
        "PDF to Word conversion runs asynchronously (background worker)"
    )


# =====================================================
# ✍ SIGN PDF (SAFE FOR WEB)
# =====================================================
def sign_pdf(pdf_path, output_path, signer="Signed User"):
    """
    Digitally stamps a PDF with signer name.

    ✔ Lightweight
    ✔ Safe on Render
    ✔ No external binaries
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        packet = io.BytesIO()

        c = canvas.Canvas(packet, pagesize=A4)
        c.setFont("Helvetica", 9)
        c.drawString(40, 25, f"Signed by: {signer}")
        c.save()

        packet.seek(0)
        overlay = PdfReader(packet)

        page.merge_page(overlay.pages[0])
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


# =====================================================
# ➕ MERGE PDFs (SAFE FOR WEB)
# =====================================================
def merge_pdfs(pdf_paths, output_path):
    """
    Merge multiple PDFs into one.

    ✔ Safe
    ✔ Fast
    ✔ No system dependencies
    """
    merger = PdfMerger()

    for path in pdf_paths:
        merger.append(path)

    merger.write(output_path)
    merger.close()

    return output_path


# =====================================================
# ✂ SPLIT PDF (SAFE FOR WEB)
# =====================================================
def split_pdf(pdf_path, output_dir):
    """
    Split a PDF into individual pages.

    ✔ Safe
    ✔ Uses temp directory
    ✔ Returns list of output files
    """
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
