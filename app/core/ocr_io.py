import os
import platform
import shutil
from pathlib import Path
import cv2
import pytesseract
def _find_tesseract() -> str | None:
    env = os.environ.get("TESSERACT_CMD")
    if env and Path(env).exists():
        return env
    which = shutil.which("tesseract")
    if which:
        return which
    system = platform.system()
    candidates: list[str] = []
    if system == "Windows":
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(
                r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"
            ),
        ]
    elif system == "Darwin":
        candidates = [
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract",
        ]
    else:
        candidates = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/snap/bin/tesseract",
        ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None
_tess_cmd = _find_tesseract()
if _tess_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tess_cmd
    print(f"[ocr] Tesseract: {_tess_cmd}")
else:
    print(
        "[ocr] ВНИМАНИЕ: Tesseract не найден. "
        "Установите его и/или задайте переменную окружения TESSERACT_CMD."
    )
if "TESSDATA_PREFIX" not in os.environ and _tess_cmd:
    tess_dir = Path(_tess_cmd).resolve().parent
    for candidate in (tess_dir / "tessdata", tess_dir.parent / "share" / "tessdata"):
        if candidate.is_dir():
            os.environ["TESSDATA_PREFIX"] = str(candidate)
            break
from app.config import settings
from app.core.preprocess import preprocess
def _russian_count(text: str) -> int:
    return sum(1 for ch in text if 'а' <= ch.lower() <= 'я' or ch == 'ё')
def _ocr_one(img) -> str:
    try:
        binary = preprocess(img, mode="light")
        return pytesseract.image_to_string(
            binary,
            lang=settings.tesseract_lang,
            config=f"--psm {settings.ocr_psm}",
        )
    except Exception as e:
        print(f"[ocr] ошибка распознавания: {e}")
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