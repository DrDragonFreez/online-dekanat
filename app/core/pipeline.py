from pathlib import Path
from app.core.service import read_text, read_marks
from app.core.extract import extract_fields
from app.core.rules import validate
from app.core.answers import build_answer
def process_document(doc_id: str, doc_type: str, path, questions: list) -> dict:
    text, _ = read_text(Path(path))
    sig, seal = read_marks(Path(path), doc_type)
    fields = extract_fields(text, doc_type)
    if "signature_present" in fields:
        fields["signature_present"] = bool(sig)
    if "seal_present" in fields:
        fields["seal_present"] = bool(seal)
    validation = validate(fields, doc_type)
    answers = []
    for q in questions:
        a = build_answer(q["question"], fields, validation)
        answers.append({
            "question_id": q["question_id"],
            "answerable": a["answerable"],
            "value": a["value"],
            "answer": a["answer"],
            "sources": a["sources"],
        })
    return {
        "document_id": doc_id,
        "document_type": doc_type,
        "fields": fields,
        "validation": validation,
        "answers": answers,
    }