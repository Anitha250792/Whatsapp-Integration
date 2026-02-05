# files/converters.py
import os
import io
import subprocess
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pdf2docx import Converter

# ===============================
# ❌ Web-disabled converters
# ===============================
def word_to_pdf(input_path, output_dir):
    subprocess.run(
        [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            input_path,
            "--outdir",
            output_dir,
        ],
        check=True,
    )

    base = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(output_dir, f"{base}.pdf")


def pdf_to_word(input_path, output_path):
    cv = Converter(input_path)
    cv.convert(output_path)
    cv.close()


# ===============================
# SAFE OPERATIONS
# ===============================
def sign_pdf(pdf_path, output_path, signer="Signed User"):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 720, "Document Signed")
    c.setFont("Helvetica", 11)
    c.drawString(72, 690, f"Signed by: {signer}")
    c.showPage()
    c.save()

    packet.seek(0)
    writer.add_page(PdfReader(packet).pages[0])

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def merge_pdfs(pdf_paths, output_path):
    merger = PdfMerger()
    for path in pdf_paths:
        merger.append(path)
    merger.write(output_path)
    merger.close()
    return output_path


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
