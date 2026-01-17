from docx import Document
from pdfminer.high_level import extract_text
from reportlab.pdfgen import canvas
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import os

# PDF ➜ Word
def word_to_pdf(docx_path, output_path):
    doc = Document(docx_path)
    c = canvas.Canvas(output_path)
    y = 800

    for para in doc.paragraphs:
        c.drawString(40, y, para.text)
        y -= 15
        if y < 40:
            c.showPage()
            y = 800

    c.save()
    return output_path

# Word ➜ PDF
def pdf_to_word(pdf_path, output_path):
    text = extract_text(pdf_path)
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(output_path)
    return output_path

def sign_pdf(pdf_path, output_path, signer="Signed by User"):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path

def merge_pdfs(pdf_paths, output_path):
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)
    merger.write(output_path)
    merger.close()
    return output_path

def split_pdf(pdf_path, output_dir):
    reader = PdfReader(pdf_path)
    paths = []

    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        output_path = os.path.join(output_dir, f"page_{i+1}.pdf")
        with open(output_path, "wb") as f:
            writer.write(f)

        paths.append(output_path)

    return paths
