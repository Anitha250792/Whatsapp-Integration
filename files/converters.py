import os
from docx import Document
from pdfminer.high_level import extract_text
from reportlab.pdfgen import canvas
from PyPDF2 import PdfMerger, PdfReader, PdfWriter

# OCR (safe imports)
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
    c = canvas.Canvas(output_path)

    width, height = 595, 842  # A4
    y = height - 40

    for para in doc.paragraphs:
        c.drawString(40, y, para.text)
        y -= 15
        if y < 40:
            c.showPage()
            y = height - 40

    c.save()
    return output_path


# ==============================
# PDF ➜ WORD (with OCR fallback)
# ==============================
def pdf_to_word(pdf_path, output_path):
    text = extract_text(pdf_path) or ""

    # 🧠 If text-based PDF
    if text.strip():
        doc = Document()
        for line in text.split("\n"):
            doc.add_paragraph(line)
        doc.save(output_path)
        return output_path

    # 🖼️ Scanned PDF → OCR required
    if not convert_from_path or not pytesseract:
        raise ValueError("Scanned PDFs need OCR support")

    images = convert_from_path(pdf_path)
    ocr_text = ""

    for img in images:
        ocr_text += pytesseract.image_to_string(img)

    if not ocr_text.strip():
        raise ValueError("Scanned PDFs need OCR")

    doc = Document()
    for line in ocr_text.split("\n"):
        doc.add_paragraph(line)

    doc.save(output_path)
    return output_path


# ==============================
# SIGN PDF
# ==============================
def sign_pdf(pdf_path, output_path, signer="Signed by User"):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
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

        out_path = os.path.join(output_dir, f"page_{i+1}.pdf")
        with open(out_path, "wb") as f:
            writer.write(f)

        output_files.append(out_path)

    return output_files
