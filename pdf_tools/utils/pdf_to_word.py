from pdfminer.high_level import extract_text
from docx import Document

def pdf_to_word(input_pdf_path, output_docx_path):
    """
    Convert PDF file to Word document
    """
    text = extract_text(input_pdf_path)

    doc = Document()
    doc.add_paragraph(text)
    doc.save(output_docx_path)

    return output_docx_path
