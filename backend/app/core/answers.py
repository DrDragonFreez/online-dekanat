import re
from backend.app.core.extract import LABELS, LABEL_TO_KEY, NOT_FOUND
_RE_COMPLETENESS = re.compile(
    r"Содержит\s+ли\s+документ\s+все\s+обязательные\s+сведения",
    re.IGNORECASE,
)
_RE_WHO_DECIDES = re.compile(
    r"Кто\s+принимает\s+окончательное\s+решение",
    re.IGNORECASE,
)
_RE_FIELD_VALUE = re.compile(
    r"Укажи\s+значение\s+поля\s*[«\"']([^»\"']+)[»\"']",
    re.IGNORECASE,
)
_RE_SEAL_QUESTION = re.compile(
    r"нужна\s+ли\s+печать|требуется\s+ли\s+печать|есть\s+ли\s+печать|"
    r"печать\s+обязательна|про\s+печать|нужна\s+печать",
    re.IGNORECASE,
)
ANSWER_NO_DATA = (
    "В документе и в Положении нет информации для ответа на этот вопрос. "
    "Обратитесь в деканат."
)
ANSWER_WHO = (
    "Окончательное решение принимает сотрудник деканата, "
    "пункт 1.3 Положения."
)
def _fmt_rules(sources: list[str]) -> str:
    nums = [s.split(":", 1)[1] for s in sources if s.startswith("rule:")]
    return ", ".join(nums)
def _missing_human(key: str, fields: dict) -> str:
    if key == "signature_present":
        if "group" in fields:
            return "подпись студента"
        if "organization" in fields:
            return "подпись руководителя"
        return "подпись сотрудника"
    if key == "seal_present":
        if "organization" in fields:
            return "печать организации"
        return "печать вуза"
    return LABELS.get(key, key).lower()
def _answer_completeness(validation: dict, fields: dict) -> dict:
    status = validation["status"]
    sources = validation["sources"]
    if status == "document_ok":
        pts = _fmt_rules(sources)
        answer = (
            f"Документ содержит все обязательные сведения по пунктам "
            f"{pts} Положения. Окончательное решение примет "
            f"сотрудник деканата."
        )
    else:
        miss = ", ".join(
            _missing_human(k, fields)
            for k in validation["missing_fields"]
        )
        pts = _fmt_rules(sources)
        answer = (
            f"Не хватает следующих сведений: {miss}. "
            f"Основание: пункты {pts} Положения."
        )
    return {
        "answerable": True,
        "value": status,
        "answer": answer,
        "sources": sources,
    }
def _answer_field(key: str, fields: dict, label: str) -> dict:
    val = fields.get(key, NOT_FOUND)
    if val == NOT_FOUND or val is None:
        return {
            "answerable": False,
            "value": None,
            "answer": f"Поле «{label}» не найдено в документе. "
                      f"Обратитесь в деканат.",
            "sources": [],
        }
    return {
        "answerable": True,
        "value": str(val),
        "answer": f"{label}: {val}.",
        "sources": [f"field:{key}"],
    }
def _no_data() -> dict:
    return {
        "answerable": False,
        "value": None,
        "answer": ANSWER_NO_DATA,
        "sources": [],
    }
def build_answer(question: str, fields: dict, validation: dict) -> dict:
    q = question.strip()
    if _RE_COMPLETENESS.search(q):
        return _answer_completeness(validation, fields)
    if _RE_WHO_DECIDES.search(q):
        return {
            "answerable": True,
            "value": "сотрудник деканата",
            "answer": ANSWER_WHO,
            "sources": ["rule:1.3"],
        }
    if _RE_SEAL_QUESTION.search(q) and "group" in fields:
        return {
            "answerable": True,
            "value": "не требуется",
            "answer": (
                "Печать вуза и подпись сотрудника деканата для "
                "предварительной проверки заявления не требуются, "
                "пункт 4.3 Положения."
            ),
            "sources": ["rule:4.3"],
        }
    m = _RE_FIELD_VALUE.search(q)
    if m:
        label = m.group(1).strip()
        key = LABEL_TO_KEY.get(label)
        if key is None:
            for k, v in LABEL_TO_KEY.items():
                if k.lower() == label.lower():
                    key = v
                    break
        if key is not None:
            return _answer_field(key, fields, label)
    return _no_data()
def generate_answers(questions: list[dict], fields: dict,
                     validation: dict) -> list[dict]:
    out = []
    for q in questions:
        a = build_answer(q["question"], fields, validation)
        out.append({
            "question_id": q["question_id"],
            "answerable": a["answerable"],
            "value": a["value"],
            "answer": a["answer"],
            "sources": a["sources"],
        })
    return out