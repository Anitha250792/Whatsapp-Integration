from PyPDF2 import PdfMerger

def merge_pdfs(input_files, output_path):
    """
    Merge multiple PDF files into one PDF
    """
    merger = PdfMerger()

    for pdf in input_files:
        merger.append(pdf)

    merger.write(output_path)
    merger.close()

    return output_path
