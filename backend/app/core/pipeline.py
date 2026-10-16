import os
from pathlib import Path
from backend.app.core.service import read_text, read_marks
from backend.app.core.extract import extract_fields, NOT_FOUND
from backend.app.core.rules import validate
from backend.app.core.answers import build_answer
USE_LLM = os.getenv("DEKANAT_USE_LLM", "0") == "1"
def _too_many_missing(fields: dict) -> bool:
    return sum(1 for v in fields.values() if v == NOT_FOUND) >= 5
def process_document(doc_id: str, doc_type: str, path, questions: list) -> dict:
    text, _ = read_text(Path(path))
    sig, seal = read_marks(Path(path), doc_type)
    fields = extract_fields(text, doc_type)
    if USE_LLM:
        all_missing = all(v == NOT_FOUND for v in fields.values()
                          if not isinstance(v, bool))
        if all_missing:
            print(f"[LLM] {doc_id}: пустой бланк, пропускаю LLM")
        elif _too_many_missing(fields):
            print(f"[LLM] {doc_id}: rules дали много пропусков, подключаю LLM...")
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