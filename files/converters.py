from docx import Document
from pdfminer.high_level import extract_text
from reportlab.pdfgen import canvas
import os

# PDF ➜ Word
def pdf_to_word(pdf_path, output_path):
    text = extract_text(pdf_path)

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)

    doc.save(output_path)
    return output_path


# Word ➜ PDF
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
