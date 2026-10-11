from pathlib import Path
import cv2
import numpy as np
def detect_marks_pdf(images: list, page_w: float, page_h: float):
    sig, seal = False, False
    for img in images:
        x0 = float(img.get("x0", 0))
        x1 = float(img.get("x1", 0))
        if x1 <= x0:
            continue
        cx = (x0 + x1) / 2.0
        rel = cx / page_w if page_w else 0.5
        if rel >= 0.6:
            seal = True
        else:
            sig = True
    return sig, seal
def detect_marks_png(path: Path):
    img = cv2.imread(str(path))
    if img is None:
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
    sig = 300 <= sig_px <= 0.10 * h * w
    seal = seal_px >= 600
    return sig, seal