import sys
from pathlib import Path
import cv2
import numpy as np
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from backend import _auto_deskew
def analyze(path):
    img = cv2.imread(str(path))
    if img is None:
        print(f"{path}: не прочиталось")
        return
    print(f"\n=== {path.name} ===")
    print(f"Исходное: {img.shape}")
    img = _auto_deskew(img)
    print(f"После deskew: {img.shape}")
    h, w = img.shape[:2]
    if w != 1200:
        scale = 1200 / w
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        img = cv2.resize(img, (1200, int(h * scale)), interpolation=interp)
    print(f"После normalize: {img.shape}")
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    for label, s_min in [("S>=40", 40), ("S>=60", 60), ("S>=80", 80), ("S>=100", 100)]:
        mask = cv2.inRange(hsv, (90, s_min, 60), (140, 255, 255))
        sig_region = mask.copy()
        sig_region[: int(h * 0.45), :] = 0
        sig_region[:, int(w * 0.60):] = 0
        seal_region = mask.copy()
        seal_region[: int(h * 0.40), :] = 0
        seal_region[:, : int(w * 0.60)] = 0
        sig_px = int(np.count_nonzero(sig_region))
        seal_px = int(np.count_nonzero(seal_region))
        print(f"  {label}: sig={sig_px}, seal={seal_px}")
for name in ["std_certificate.png", "open-010.png"]:
    p = ROOT / "data" / "documents" / name
    if p.exists():
        analyze(p)
    else:
        print(f"Нет файла: {p}")