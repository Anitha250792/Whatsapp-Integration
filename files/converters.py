from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

def word_to_pdf(word_path, pdf_path):
    doc = Document(word_path)
    c = canvas.Canvas(pdf_path, pagesize=A4)

    width, height = A4
    y = height - 40

    for para in doc.paragraphs:
        c.drawString(40, y, para.text)
        y -= 20
        if y < 40:
            c.showPage()
            y = height - 40

    c.save()
