from pathlib import Path
import cv2
import numpy as np
SIG_THRESHOLD = {
    "study_certificate": 5800,
    "academic_leave_application": 2500,
    "internship_certificate": 5800,
}
SEAL_THRESHOLD = 2000
DEFAULT_SIG_THRESHOLD = 5800
def _detect_from_image(img: np.ndarray, doc_type: str | None = None):
    if img is None or img.size == 0:
        return False, False
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (90, 40, 40), (140, 255, 255))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    sig_region = mask.copy()
    sig_region[: int(h * 0.45), :] = 0
    sig_region[:, int(w * 0.60):] = 0
    seal_region = mask.copy()
    seal_region[: int(h * 0.40), :] = 0
    seal_region[:, : int(w * 0.60)] = 0
    sig_px = int(np.count_nonzero(sig_region))
    seal_px = int(np.count_nonzero(seal_region))
    sig_th = SIG_THRESHOLD.get(doc_type or "", DEFAULT_SIG_THRESHOLD)
    return sig_px >= sig_th, seal_px >= SEAL_THRESHOLD
def detect_marks_png(path: Path, doc_type: str | None = None):
    img = cv2.imread(str(path))
    return _detect_from_image(img, doc_type)
def detect_marks_pdf(path: Path, doc_type: str | None = None):
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return False, False
    pdf = pdfium.PdfDocument(str(path))
    try:
        page = pdf[0]
        bitmap = page.render(scale=2.0)
        pil_image = bitmap.to_pil()
    finally:
        pdf.close()
    img = np.array(pil_image)
    if img.ndim == 3 and img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif img.ndim == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    return _detect_from_image(img, doc_type)