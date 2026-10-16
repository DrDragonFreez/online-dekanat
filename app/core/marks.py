from pathlib import Path
import cv2
import numpy as np
SIG_THRESHOLD = 500
SEAL_THRESHOLD = 1500
def _normalize_size(img, target_width=1200):
    h, w = img.shape[:2]
    if w == target_width:
        return img
    scale = target_width / w
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    return cv2.resize(img, (target_width, int(h * scale)), interpolation=interp)
def _thresholds_for(doc_type):
    try:
        from app.core.config_loader import get_type
        cfg = get_type(doc_type)
        m = cfg.get("marks", {}) or {}
        return (
            int(m.get("sig_threshold", SIG_THRESHOLD)),
            int(m.get("seal_threshold", SEAL_THRESHOLD)),
        )
    except Exception:
        return SIG_THRESHOLD, SEAL_THRESHOLD
def _strict_detect(img, doc_type=None, kind="pdf"):
    if img is None or img.size == 0:
        return False, False
    img = _normalize_size(img)
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (90, 80, 60), (140, 255, 255))
    sig_region = mask.copy()
    sig_region[: int(h * 0.45), :] = 0
    sig_region[:, int(w * 0.60):] = 0
    seal_region = mask.copy()
    seal_region[: int(h * 0.40), :] = 0
    seal_region[:, : int(w * 0.60)] = 0
    sig_px = int(np.count_nonzero(sig_region))
    seal_px = int(np.count_nonzero(seal_region))
    sig_th, seal_th = _thresholds_for(doc_type)
    print(f"[marks-strict] {doc_type} ({kind}): sig={sig_px} (th={sig_th}), seal={seal_px} (th={seal_th})")
    return sig_px >= sig_th, seal_px >= seal_th
def _auto_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    blue = cv2.inRange(hsv, (90, 30, 30), (150, 255, 255))
    if np.count_nonzero(blue) > 500:
        return blue
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, dark = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    return dark
def _classify_cluster(comp, page_area):
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
def _loose_detect(img):
    if img is None or img.size == 0:
        return False, False
    h, w = img.shape[:2]
    if w < 1500:
        scale = 1500 / w
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        img = cv2.resize(img, (1500, int(h * scale)), interpolation=interp)
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
    print(f"[marks-loose] sig={sig_found}, seal={seal_found}")
    return sig_found, seal_found
def detect_marks_png(path, doc_type=None, mode="strict"):
    img = cv2.imread(str(path))
    if img is None:
        return False, False
    if mode == "loose":
        return _loose_detect(img)
    return _strict_detect(img, doc_type, kind="png")
def detect_marks_pdf(path, doc_type=None, mode="strict"):
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
    if mode == "loose":
        return _loose_detect(img)
    return _strict_detect(img, doc_type, kind="pdf")