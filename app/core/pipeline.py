from pathlib import Path

from app.core.service import read_document
from app.core.extract import extract_fields
from app.core.rules import validate
from app.core.answers import build_answer

def process_document(doc_id: str, doc_type: str, path, questions: list) -> dict:
    text, sig, seal, _ = read_document(Path(path))

    fields = extract_fields(text, doc_type)
    if "signature_present" in fields:
        fields["signature_present"] = sig
    if "seal_present" in fields:
        fields["seal_present"] = seal

    validation = validate(fields, doc_type)

    answers = []
    for q in questions:
        a = build_answer(q["question"], fields, validation)
        answers.append({
            "question_id": q["question_id"],
            "answerable": a["answerable"],
            "value": a["value"],
            "answer": a["answer"],
            "source": a["source"],
        })

    return {
        "document_id": doc_id,
        "document_type": doc_type,
        "fields": fields,
        "validation": validation,
        "answers": answers,
    }

