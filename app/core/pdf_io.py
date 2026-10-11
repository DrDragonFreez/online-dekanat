from pathlib import Path
import pdfplumber
def read_pdf(path: Path):
    with pdfplumber.open(str(path)) as pdf:
        page = pdf.pages[0]
        text = page.extract_text() or ""
        images = list(page.images)
        return text, images, page.width, page.height