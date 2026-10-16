import re
import tempfile
from pathlib import Path
import cv2
from backend.app.core.pdf_io import read_pdf
from backend.app.core.ocr_io import read_image_ocr
from backend.app.core.marks import detect_marks_pdf, detect_marks_png
from backend.app.core.text_post import postprocess
from backend.app.core.normalize_text import normalize as normalize_text
from backend.app.core.classifier import classify
from backend.app.core.extract import extract_fields, NOT_FOUND
from backend.app.core.rules import validate
from backend.app.core.answers import build_answer
from backend.app.core.preprocess import _auto_deskew
def _is_blank_form(text, fields):
    if not text:
        return True
    long_underscores = re.findall(r"_{5,}", text)
    if len(long_underscores) >= 4:
        return True
    return False
def read_text(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        text, _i, _W, _H = read_pdf(path)
        kind = "pdf"
    else:
        text = read_image_ocr(path)
        kind = "image"
    return normalize_text(postprocess(text)), kind
def _deskew_for_marks(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return path
    img = cv2.imread(str(path))
    if img is None:
        return path
    deskewed = _auto_deskew(img)
    if deskewed is None:
        return path
    tmp = Path(tempfile.gettempdir()) / f"deskew_{path.stem}.png"
    cv2.imwrite(str(tmp), deskewed)
    return tmp
def read_marks(path, doc_type, mode="strict"):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return detect_marks_pdf(path, doc_type=doc_type, mode=mode)
    return detect_marks_png(path, doc_type=doc_type, mode=mode)
def process_full(path, question="", doc_type=None, marks_mode="strict", use_llm=False):
    text, kind = read_text(Path(path))
    if doc_type is None:
        doc_type = classify(text)
    marks_path = _deskew_for_marks(Path(path))
    sig, seal = read_marks(marks_path, doc_type, mode=marks_mode)
    fields = extract_fields(text, doc_type)
    is_blank = _is_blank_form(text, fields)
    if use_llm and is_blank:
        print("[LLM] пустой бланк — пропускаю LLM")
        use_llm = False
    if use_llm:
        text_keys = [k for k, v in fields.items() if not isinstance(v, bool)]
        missing = sum(1 for k in text_keys if fields[k] == NOT_FOUND)
        if missing >= 4:
            print(f"[LLM] {missing} полей не найдено — подключаю LLM...")
            try:
                from backend.app.core.llm_extract import extract_fields_llm
                llm_fields = extract_fields_llm(text, doc_type)
                for k, v in llm_fields.items():
                    if k in fields and fields[k] == NOT_FOUND and v != NOT_FOUND:
                        fields[k] = v
                        print(f"[LLM]   {k}: {v!r}")
            except Exception as exc:
                print(f"[LLM] ошибка: {exc}")
    if "signature_present" in fields:
        fields["signature_present"] = bool(sig)
    if "seal_present" in fields:
        fields["seal_present"] = bool(seal)
    validation = validate(fields, doc_type)
    answer = build_answer(question, fields, validation) if question else None
    return {
        "text": text,
        "doc_type": doc_type,
        "fields": fields,
        "validation": validation,
        "answer": answer,
        "kind": kind,
        "marks_mode": marks_mode,
    }
def process_one(path, question="", doc_type=None, marks_mode="strict", use_llm=False):
    return process_full(path, question, doc_type, marks_mode, use_llm)