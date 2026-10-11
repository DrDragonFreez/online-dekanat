import cv2
import numpy as np
def _upscale_if_small(img: np.ndarray, min_width: int = 1500) -> np.ndarray:
    h, w = img.shape[:2]
    if w < min_width:
        scale = min_width / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_CUBIC)
    return img
def preprocess_light(img: np.ndarray) -> np.ndarray:
    img = _upscale_if_small(img)
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
def _deskew(img: np.ndarray, max_angle: float = 30.0) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255,
                           cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 100:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5 or abs(angle) > max_angle:
        return img
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)
def _normalize_shadows(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bg = cv2.dilate(gray, np.ones((7, 7), np.uint8), iterations=2)
    bg = cv2.medianBlur(bg, 21)
    normalized = cv2.divide(gray, bg, scale=255)
    return cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
def _denoise(img: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
def preprocess_hard(img: np.ndarray) -> np.ndarray:
    img = _upscale_if_small(img)
    img = _remove_glare(img)
    img = _denoise(img)
    img = _deskew(img)
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
    if mode == "light":
        return preprocess_light(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    contrast = float(gray.std())
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if contrast < 40 or laplacian_var < 100:
        return preprocess_hard(img)
    return preprocess_light(img)