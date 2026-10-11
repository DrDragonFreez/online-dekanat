import os
from pathlib import Path
import pytesseract
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
os.environ.setdefault(
    "TESSDATA_PREFIX",
    r"C:\Program Files\Tesseract-OCR\tessdata",
)
from app.config import settings
from app.core.preprocess import preprocess
def read_image_ocr(path: Path) -> str:
    binary = preprocess(path)
    cfg = f"--psm {settings.ocr_psm}"
    text = pytesseract.image_to_string(
        binary, lang=settings.tesseract_lang, config=cfg)
    return text