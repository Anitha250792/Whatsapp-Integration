from docx import Document
from reportlab.pdfgen import canvas

def word_to_pdf(docx_path, output_pdf):
    """
    Simple Word to PDF conversion (text-only)
    """
    doc = Document(docx_path)

    c = canvas.Canvas(output_pdf)
    y = 800

    for para in doc.paragraphs:
        c.drawString(40, y, para.text)
        y -= 15
        if y < 40:
            c.showPage()
            y = 800

    c.save()

    return output_pdf
