from pathlib import Path
from app.core.pdf_io import read_pdf
from app.core.ocr_io import read_image_ocr
from app.core.marks import detect_marks_pdf, detect_marks_png
from app.core.text_post import postprocess
from app.core.classifier import classify
from app.core.extract import extract_fields
from app.core.rules import validate
from app.core.answers import build_answer
def read_document(path: Path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        text, images, W, H = read_pdf(path)
        sig, seal = detect_marks_pdf(images, W, H)
        kind = "pdf"
    else:
        text = read_image_ocr(path)
        sig, seal = detect_marks_png(path)
        kind = "images"
    return postprocess(text), bool(sig), bool(seal), kind
def process_full(path: Path, question: str = "",
                 doc_type: str | None = None) -> dict:
    text, sig, seal, kind = read_document(Path(path))
    if doc_type is None:
        doc_type = classify(text)
    fields = extract_fields(text, doc_type)
    if "signature_present" in fields:
        fields["signature_present"] = sig
    if "seal_present" in fields:
        fields["seal_present"] = seal
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
def process_one(path: Path, question: str = "",
                 doc_type: str | None = None) -> dict:
    return process_full(path, question, doc_type)
