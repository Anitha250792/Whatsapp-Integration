from PyPDF2 import PdfReader, PdfWriter
import os

def split_pdf(input_file, output_dir):
    """
    Split a PDF into individual pages
    """
    reader = PdfReader(input_file)
    output_files = []

    for index, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        output_path = os.path.join(output_dir, f"page_{index + 1}.pdf")

        with open(output_path, "wb") as f:
            writer.write(f)

        output_files.append(output_path)

    return output_files
