from pathlib import Path
from ultralytics import YOLO
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModelForObjectDetection
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
SIG_MODEL_PATH = MODELS_DIR / "yolov11-signature-corporate.pt"
_sig_model = None
def _get_sig_model():
    global _sig_model
    if _sig_model is None:
        if not SIG_MODEL_PATH.exists():
            raise FileNotFoundError(f"Нет модели подписи: {SIG_MODEL_PATH}")
        _sig_model = YOLO(str(SIG_MODEL_PATH))
    return _sig_model
STAMP_MODEL_DIR = MODELS_DIR / "ooredoo-stamp"
_stamp_processor = None
_stamp_model = None
def _get_stamp_model():
    global _stamp_processor, _stamp_model
    if _stamp_model is None:
        if not STAMP_MODEL_DIR.exists():
            raise FileNotFoundError(f"Нет модели печати: {STAMP_MODEL_DIR}")
        _stamp_processor = AutoImageProcessor.from_pretrained(str(STAMP_MODEL_DIR))
        _stamp_model = AutoModelForObjectDetection.from_pretrained(str(STAMP_MODEL_DIR))
        _stamp_model.eval()
    return _stamp_processor, _stamp_model
def detect_signature(path: Path, conf_threshold: float = 0.5) -> bool:
    model = _get_sig_model()
    results = model(str(path), verbose=False)[0]
    for box in results.boxes:
        if float(box.conf[0]) >= conf_threshold:
            return True
    return False
def detect_stamp(path: Path, conf_threshold: float = 0.5) -> bool:
    processor, model = _get_stamp_model()
    image = Image.open(path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    target_sizes = torch.tensor([image.size[::-1]])
    results = processor.post_process_object_detection(
        outputs, target_sizes=target_sizes, threshold=conf_threshold,
    )[0]
    return len(results["scores"]) > 0
def detect_marks_cnn(path: Path):
    sig = detect_signature(path)
    seal = detect_stamp(path)
    return sig, seal