from reportlab.pdfgen import canvas



def sign_pdf(output_path, signature_text="Digitally Signed"):
    """
    Add a digital signature text to PDF
    """
    c = canvas.Canvas(output_path)
    c.drawString(100, 50, signature_text)
    c.save()

    return output_path
