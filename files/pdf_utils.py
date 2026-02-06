from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter

def sign_pdf(input_path, output_path, signer):
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Create signature overlay
    packet_path = output_path + "_sig.pdf"
    c = canvas.Canvas(packet_path)
    c.drawString(100, 50, f"Signed by: {signer}")
    c.save()

    sig_reader = PdfReader(packet_path)
    writer.pages[0].merge_page(sig_reader.pages[0])

    with open(output_path, "wb") as f:
        writer.write(f)
