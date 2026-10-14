import re
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from app.config import settings
from app.core.preprocess import _upscale_if_small, _auto_deskew
_PALETTE = [
    (255, 122, 0),
    (89, 199, 52),
    (10, 159, 255),
    (48, 59, 255),
    (222, 82, 175),
    (0, 165, 255),
    (170, 100, 240),
    (40, 200, 200),
]
def _normalize(s: str) -> str:
    s = s.lower().replace("ё", "е")
    s = s.replace(".", "").replace("-", " ").replace("/", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,:;—")
def _load_as_bgr(path: Path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        try:
            import pypdfium2 as pdfium
        except ImportError:
            return None
        try:
            pdf = pdfium.PdfDocument(str(path))
            page = pdf[0]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            pdf.close()
        except Exception:
            return None
        img = np.array(pil_image)
        if img.ndim == 3 and img.shape[2] == 3:
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        if img.ndim == 3 and img.shape[2] == 4:
            return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        return None
    return cv2.imread(str(path))
def _extract_words(img) -> list[dict]:
    data = pytesseract.image_to_data(
        img,
        lang=settings.tesseract_lang,
        config=f"--psm {settings.ocr_psm}",
        output_type=pytesseract.Output.DICT,
    )
    words = []
    for i in range(len(data["text"])):
        t = data["text"][i].strip()
        if not t:
            continue
        try:
            conf = int(data["conf"][i])
        except (ValueError, TypeError):
            conf = 0
        if conf < 30:
            continue
        words.append({
            "text": t,
            "x": int(data["left"][i]),
            "y": int(data["top"][i]),
            "w": int(data["width"][i]),
            "h": int(data["height"][i]),
            "block": int(data["block_num"][i]),
            "par": int(data["par_num"][i]),
            "line": int(data["line_num"][i]),
        })
    return words
def _group_lines(words: list[dict]) -> list[list[dict]]:
    from collections import defaultdict
    buckets = defaultdict(list)
    for w in words:
        buckets[(w["block"], w["par"], w["line"])].append(w)
    lines = list(buckets.values())
    for ln in lines:
        ln.sort(key=lambda w: w["x"])
    lines.sort(key=lambda ln: ln[0]["y"] if ln else 0)
    return lines
def _match_label_in_line(line: list[dict], label: str) -> bool:
    label_norm = _normalize(label)
    joined = " ".join(w["text"] for w in line)
    return label_norm in _normalize(joined)
def _bbox_of_line(line: list[dict]) -> tuple[int, int, int, int]:
    xs1 = [w["x"] for w in line]
    ys1 = [w["y"] for w in line]
    xs2 = [w["x"] + w["w"] for w in line]
    ys2 = [w["y"] + w["h"] for w in line]
    return min(xs1), min(ys1), max(xs2), max(ys2)
def _draw_label(img, x1: int, y1: int, x2: int, text: str, color):
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.42
    thick = 1
    (tw, th), _ = cv2.getTextSize(text, font, scale, thick)
    pad_x = 5
    pad_y = 3
    top = y1 + 2
    bottom = top + th + pad_y * 2
    left = x1 + 2
    right = left + tw + pad_x * 2
    if right > x2 - 2:
        right = x2 - 2
    if bottom > img.shape[0]:
        bottom = img.shape[0]
    overlay = img.copy()
    cv2.rectangle(overlay, (left, top), (right, bottom), color, -1)
    cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)
    cv2.putText(img, text, (left + pad_x, bottom - pad_y),
                font, scale, (255, 255, 255), thick, cv2.LINE_AA)
def _find_marks_bboxes(img) -> dict:
    h, w = img.shape[:2]
    page_area = h * w
    y_threshold = int(h * 0.55)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (90, 40, 40), (140, 255, 255))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    mask[:y_threshold, :] = 0
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_h, iterations=2)
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_v, iterations=1)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    sig_bbox = None
    seal_bbox = None
    best_sig_area = 0
    best_seal_area = 0
    for i in range(1, num):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 100:
            continue
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        cw = stats[i, cv2.CC_STAT_WIDTH]
        ch = stats[i, cv2.CC_STAT_HEIGHT]
        if cw == 0 or ch == 0:
            continue
        aspect = cw / ch
        fill_ratio = area / (cw * ch)
        if (area >= 2000
                and 0.5 <= aspect <= 2.0
                and 0.05 <= fill_ratio <= 0.65
                and area <= 0.5 * page_area):
            comp = (labels[y:y+ch, x:x+cw] == i).astype(np.uint8) * 255
            contours, _ = cv2.findContours(
                comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                c = max(contours, key=cv2.contourArea)
                peri = cv2.arcLength(c, True)
                if peri > 0:
                    circularity = 4 * np.pi * area / (peri ** 2)
                    if circularity > 0.25 and area > best_seal_area:
                        seal_bbox = (x, y, x + cw, y + ch)
                        best_seal_area = area
        elif (2.5 <= aspect <= 12.0
                and cw >= 80
                and 25 <= ch <= 150
                and 100 <= area <= 0.15 * page_area):
            if area > best_sig_area:
                sig_bbox = (x, y, x + cw, y + ch)
                best_sig_area = area
    result = {}
    if sig_bbox:
        result["signature_present"] = sig_bbox
    if seal_bbox:
        result["seal_present"] = seal_bbox
    return result
def highlight_fields(
    path: Path,
    fields: dict,
    labels: dict[str, str],
    out_path: Path,
    mode: str = "all",
    missing_fields: set | None = None,
) -> Path | None:
    missing_fields = set(missing_fields or [])
    print(f"[highlight] mode={mode}, missing={missing_fields}")
    img = _load_as_bgr(path)
    if img is None:
        print("[highlight] не смог загрузить файл")
        return None
    oriented = _auto_deskew(img)
    oriented = _upscale_if_small(oriented)
    gray = cv2.cvtColor(oriented, cv2.COLOR_BGR2GRAY)
    words = _extract_words(gray)
    lines = _group_lines(words) if words else []
    print(f"[highlight] слов: {len(words)}, строк: {len(lines)}")
    drawn = 0
    used_lines: set[int] = set()
    for idx, (key, value) in enumerate(fields.items()):
        if isinstance(value, bool):
            continue
        is_problem = key in missing_fields
        if mode == "problems":
            if not is_problem:
                continue
        else:
            if value is None or (
                isinstance(value, str) and value.strip() in ("", "не найдено")
            ):
                continue
        label = labels.get(key, key)
        found_line = False
        for li, line in enumerate(lines):
            if li in used_lines:
                continue
            if _match_label_in_line(line, label):
                x1, y1, x2, y2 = _bbox_of_line(line)
                pad = 3
                x1 = max(0, x1 - pad)
                y1 = max(0, y1 - pad)
                x2 = min(oriented.shape[1] - 1, x2 + pad)
                y2 = min(oriented.shape[0] - 1, y2 + pad)
                if is_problem:
                    color = (48, 59, 255)
                    text = f"{label} · не найдено"
                else:
                    color = _PALETTE[idx % len(_PALETTE)]
                    text = label
                cv2.rectangle(oriented, (x1, y1), (x2, y2), color, 2)
                _draw_label(oriented, x1, y1, x2, text, color)
                used_lines.add(li)
                drawn += 1
                found_line = True
                break
        if is_problem and not found_line:
            print(f"[highlight] метка '{label}' не найдена в тексте")
    if mode == "all":
        marks = _find_marks_bboxes(oriented)
        for key, bbox in marks.items():
            if not fields.get(key):
                continue
            label = "Подпись" if key == "signature_present" else "Печать"
            x1, y1, x2, y2 = bbox
            pad = 6
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(oriented.shape[1] - 1, x2 + pad)
            y2 = min(oriented.shape[0] - 1, y2 + pad)
            color = (48, 59, 255) if key == "signature_present" else (89, 199, 52)
            cv2.rectangle(oriented, (x1, y1), (x2, y2), color, 3)
            _draw_label(oriented, x1, y1, x2, label, color)
            drawn += 1
    else:
        h, w = oriented.shape[:2]
        color = (48, 59, 255)
        if "signature_present" in missing_fields:
            x1 = int(w * 0.08)
            y1 = int(h * 0.72)
            x2 = int(w * 0.55)
            y2 = int(h * 0.90)
            cv2.rectangle(oriented, (x1, y1), (x2, y2), color, 3)
            _draw_label(oriented, x1, y1, x2, "Подпись · не найдена", color)
            drawn += 1
        if "seal_present" in missing_fields:
            x1 = int(w * 0.65)
            y1 = int(h * 0.72)
            x2 = int(w * 0.95)
            y2 = int(h * 0.92)
            cv2.rectangle(oriented, (x1, y1), (x2, y2), color, 3)
            _draw_label(oriented, x1, y1, x2, "Печать · не найдена", color)
            drawn += 1
    print(f"[highlight] нарисовано прямоугольников: {drawn}")
    if drawn == 0:
        return None
    cv2.imwrite(str(out_path), oriented)
    return out_path