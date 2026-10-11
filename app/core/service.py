from pathlib import Path
from app.core.pdf_io import read_pdf
from app.core.ocr_io import read_image_ocr
from app.core.marks import detect_marks_pdf, detect_marks_png
from app.core.text_post import postprocess
from app.core.classifier import classify
from app.core.extract import extract_fields
from app.core.rules import validate
from app.core.answers import build_answer
def read_text(path: Path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        text, _images, _W, _H = read_pdf(path)
        kind = "pdf"
    else:
        text = read_image_ocr(path)
        kind = "image"
    return postprocess(text), kind
def read_marks(path: Path, doc_type: str):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return detect_marks_pdf(path, doc_type=doc_type)
    else:
        return detect_marks_png(path, doc_type=doc_type)
def process_full(path, question: str = "", doc_type: str | None = None) -> dict:
    text, kind = read_text(Path(path))
    if doc_type is None:
        doc_type = classify(text)
    sig, seal = read_marks(Path(path), doc_type)
    fields = extract_fields(text, doc_type)
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
    }
def process_one(path, question: str = "", doc_type: str | None = None) -> dict:
    return process_full(path, question, doc_type)