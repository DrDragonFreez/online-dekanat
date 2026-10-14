import os
from pathlib import Path
import cv2
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
def _russian_count(text: str) -> int:
    return sum(1 for ch in text if 'а' <= ch.lower() <= 'я' or ch == 'ё')
def _ocr_one(img) -> str:
    try:
        binary = preprocess(img, mode="light")
        return pytesseract.image_to_string(
            binary, lang=settings.tesseract_lang,
            config=f"--psm {settings.ocr_psm}",
        )
    except Exception:
        return ""
def read_image_ocr(path: Path) -> str:
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Не могу прочитать: {path}")
    text = _ocr_one(img)
    best_score = _russian_count(text)
    best_text = text
    if best_score >= 100:
        return text
    for rotation in (
        cv2.ROTATE_90_CLOCKWISE,
        cv2.ROTATE_180,
        cv2.ROTATE_90_COUNTERCLOCKWISE,
    ):
        rotated = cv2.rotate(img, rotation)
        candidate = _ocr_one(rotated)
        score = _russian_count(candidate)
        if score > best_score:
            best_score = score
            best_text = candidate
    return best_text