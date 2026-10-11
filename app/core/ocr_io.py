import os
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from app.config import settings
def _preprocess(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    _, th = cv2.threshold(gray, 0, 255,
                          cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return th
def read_image_ocr(path: Path) -> str:
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Не могу прочитать: {path}")
    h, w = img.shape[:2]
    if w < 1500:
        scale = 1500 / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_CUBIC)
    proc = _preprocess(img)
    cfg = f"--psm {settings.ocr_psm}"
    text = pytesseract.image_to_string(
        proc, lang=settings.tesseract_lang, config=cfg)
    return text