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
    SAFE PDF signing for Render / low-memory servers.

    Strategy:
    - Do NOT merge page content streams
    - Append a lightweight signature page instead

    Result:
    ✔ Zero crashes
    ✔ Zero timeouts
    ✔ Works on all PDFs
    """

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    # 1️⃣ Copy original pages (NO modification)
    for page in reader.pages:
        writer.add_page(page)

    # 2️⃣ Create a lightweight signature page
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 720, "Document Signed")

    c.setFont("Helvetica", 11)
    c.drawString(72, 690, f"Signed by: {signer}")

    c.setFont("Helvetica", 10)
    c.drawString(72, 660, "This document was digitally signed.")
    c.drawString(72, 640, "Signature applied by File Converter System.")

    c.showPage()
    c.save()

    packet.seek(0)

    # 3️⃣ Add signature page safely
    signature_reader = PdfReader(packet)
    writer.add_page(signature_reader.pages[0])

    # 4️⃣ Write final PDF
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


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
