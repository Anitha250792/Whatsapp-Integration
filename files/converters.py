import os
import io

from docx import Document
from pdfminer.high_level import extract_text
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from PyPDF2 import PdfMerger, PdfReader, PdfWriter

# OCR (optional dependencies)
try:
    from pdf2image import convert_from_path
    import pytesseract
except ImportError:
    convert_from_path = None
    pytesseract = None


# ==============================
# WORD ➜ PDF
# ==============================
def word_to_pdf(docx_path, output_path):
    doc = Document(docx_path)

    pdf = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    heading = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        spaceAfter=10,
    )

    story = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if para.style.name.startswith("Heading"):
            story.append(Paragraph(f"<b>{text}</b>", heading))
        else:
            story.append(Paragraph(text, normal))

    pdf.build(story)
    return output_path


# ==============================
# PDF ➜ WORD
# ==============================
def pdf_to_word(pdf_path, output_path):
    text = extract_text(pdf_path)

    # ✅ Normal text-based PDF
    if text and text.strip():
        doc = Document()
        for line in text.split("\n"):
            if line.strip():
                doc.add_paragraph(line)
        doc.save(output_path)
        return output_path

    # ❌ Scanned PDF → OCR fallback
    if not convert_from_path or not pytesseract:
        raise ValueError("Scanned PDF detected. OCR dependencies not installed.")

    images = convert_from_path(pdf_path)
    doc = Document()
    found_text = False

    for img in images:
        extracted = pytesseract.image_to_string(img)
        if extracted.strip():
            doc.add_paragraph(extracted)
            found_text = True

    if not found_text:
        raise ValueError("No readable text found in scanned PDF.")

    doc.save(output_path)
    return output_path


# ==============================
# SIGN PDF
# ==============================
def sign_pdf(pdf_path, output_path, signer="Signed User"):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=A4)
        can.setFont("Helvetica", 10)
        can.drawString(40, 30, f"Signed by: {signer}")
        can.save()

        packet.seek(0)
        overlay = PdfReader(packet)
        page.merge_page(overlay.pages[0])
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


# ==============================
# MERGE PDFs
# ==============================
def merge_pdfs(pdf_paths, output_path):
    merger = PdfMerger()

    for pdf in pdf_paths:
        merger.append(pdf)

    merger.write(output_path)
    merger.close()
    return output_path


# ==============================
# SPLIT PDF
# ==============================
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
