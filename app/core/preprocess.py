import cv2
import numpy as np
def _to_bgr(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img
def _upscale_if_small(img: np.ndarray, min_width: int = 1500) -> np.ndarray:
    h, w = img.shape[:2]
    if w < min_width:
        scale = min_width / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_CUBIC)
    return img
def _rotate_keep_all(img: np.ndarray, angle: float) -> np.ndarray:
    h, w = img.shape[:2]
    cos = abs(np.cos(np.radians(angle)))
    sin = abs(np.sin(np.radians(angle)))
    new_w = int(w * cos + h * sin) + 1
    new_h = int(h * cos + w * sin) + 1
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    M[0, 2] += (new_w - w) / 2
    M[1, 2] += (new_h - h) / 2
    return cv2.warpAffine(
        img, M, (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
def _crop_white_borders(img: np.ndarray, thresh: int = 245,
                        pad: int = 40) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = gray < thresh
    if not mask.any():
        return img
    ys, xs = np.where(mask)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    h, w = img.shape[:2]
    y0 = max(0, y0 - pad)
    x0 = max(0, x0 - pad)
    y1 = min(h, y1 + pad + 1)
    x1 = min(w, x1 + pad + 1)
    return img[y0:y1, x0:x1]
def _estimate_skew_angle(gray: np.ndarray) -> float:
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=31, C=15,
    )
    binary = cv2.medianBlur(binary, 3)
    lines = cv2.HoughLinesP(
        binary, 1, np.pi / 180,
        threshold=150,
        minLineLength=150,
        maxLineGap=15,
    )
    if lines is None:
        return 0.0
    lines = lines.reshape(-1, 4)
    angles = []
    for x1, y1, x2, y2 in lines:
        if x2 == x1:
            continue
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if -45 < angle < 45:
            angles.append(angle)
    if not angles:
        return 0.0
    bins = np.arange(-46, 47, 1.0)
    hist, edges = np.histogram(angles, bins=bins)
    if hist.sum() == 0:
        return 0.0
    best_idx = int(np.argmax(hist))
    return float((edges[best_idx] + edges[best_idx + 1]) / 2.0)
def _auto_deskew(img: np.ndarray, max_angle: float = 45.0,
                 max_iter: int = 3) -> np.ndarray:
    for _ in range(max_iter):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        angle = _estimate_skew_angle(gray)
        if abs(angle) < 0.3 or abs(angle) > max_angle:
            break
        img = _rotate_keep_all(img, angle)
    return _crop_white_borders(img)
def preprocess_light(img: np.ndarray) -> np.ndarray:
    img = _to_bgr(img)
    img = _upscale_if_small(img)
    img = _auto_deskew(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return binary
def _remove_glare(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    _, glare_mask = cv2.threshold(v, 240, 255, cv2.THRESH_BINARY)
    glare_mask = cv2.dilate(glare_mask, np.ones((3, 3), np.uint8), iterations=2)
    if np.count_nonzero(glare_mask) < 100:
        return img
    return cv2.inpaint(img, glare_mask, 3, cv2.INPAINT_TELEA)
def _normalize_shadows(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bg = cv2.dilate(gray, np.ones((7, 7), np.uint8), iterations=2)
    bg = cv2.medianBlur(bg, 21)
    normalized = cv2.divide(gray, bg, scale=255)
    return cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
def _denoise(img: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
def preprocess_hard(img: np.ndarray) -> np.ndarray:
    img = _to_bgr(img)
    img = _upscale_if_small(img)
    img = _remove_glare(img)
    img = _denoise(img)
    img = _auto_deskew(img)
    img = _normalize_shadows(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31, C=10,
    )
    return binary
def preprocess(path_or_img, mode: str = "light"):
    if isinstance(path_or_img, (str, bytes)) or hasattr(path_or_img, "suffix"):
        img = cv2.imread(str(path_or_img))
        if img is None:
            raise FileNotFoundError(f"Не могу прочитать: {path_or_img}")
    else:
        img = path_or_img
    if mode == "hard":
        return preprocess_hard(img)
    return preprocess_light(img)