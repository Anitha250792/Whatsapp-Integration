from docx import Document
from pdfminer.high_level import extract_text

def pdf_to_word(pdf_path, output_path):
    text = extract_text(pdf_path)

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)

    doc.save(output_path)
    return output_path
