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
def _strict_detect(img: np.ndarray, doc_type: str | None = None):
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
def _auto_mask(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    blue = cv2.inRange(hsv, (90, 30, 30), (150, 255, 255))
    if np.count_nonzero(blue) > 500:
        return blue
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, dark = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    return dark
def _classify_cluster(comp: np.ndarray, page_area: int) -> str:
    area = int(np.count_nonzero(comp))
    if area < 200:
        return "other"
    ys, xs = np.where(comp > 0)
    if len(ys) < 50:
        return "other"
    bbox_w = int(xs.max() - xs.min()) + 1
    bbox_h = int(ys.max() - ys.min()) + 1
    if bbox_w == 0 or bbox_h == 0:
        return "other"
    aspect = bbox_w / bbox_h
    fill_ratio = area / (bbox_w * bbox_h)
    if (area >= 3000 and 0.05 <= fill_ratio <= 0.65
            and 0.4 <= aspect <= 2.5 and area <= 0.5 * page_area):
        contours, _ = cv2.findContours(
            comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            peri = cv2.arcLength(c, True)
            if peri > 0:
                circularity = 4 * np.pi * area / (peri ** 2)
                if circularity > 0.25:
                    return "seal"
    if (aspect >= 3.0 and bbox_w >= 100 and bbox_h <= 100
            and 300 <= area <= 0.15 * page_area):
        return "signature"
    return "other"
def _loose_detect(img: np.ndarray):
    if img is None or img.size == 0:
        return False, False
    h, w = img.shape[:2]
    page_area = h * w
    mask = _auto_mask(img)
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
        iterations=2,
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                            np.ones((3, 3), np.uint8), iterations=1)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    sig_found = False
    seal_found = False
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] < 200:
            continue
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        cw = stats[i, cv2.CC_STAT_WIDTH]
        ch = stats[i, cv2.CC_STAT_HEIGHT]
        comp = (labels[y:y+ch, x:x+cw] == i).astype(np.uint8) * 255
        kind = _classify_cluster(comp, page_area)
        if kind == "signature":
            sig_found = True
        elif kind == "seal":
            seal_found = True
        if sig_found and seal_found:
            break
    return sig_found, seal_found
def _detect(img: np.ndarray, doc_type: str | None, mode: str):
    if mode == "loose":
        return _loose_detect(img)
    return _strict_detect(img, doc_type)
def detect_marks_png(path: Path, doc_type: str | None = None,
                     mode: str = "strict"):
    img = cv2.imread(str(path))
    return _detect(img, doc_type, mode)
def detect_marks_pdf(path: Path, doc_type: str | None = None,
                     mode: str = "strict"):
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
    return _detect(img, doc_type, mode)