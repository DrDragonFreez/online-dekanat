import re

from app.core.extract import LABELS, LABEL_TO_KEY, NOT_FOUND

_RE_COMPLETENESS = re.compile(
    r"Содержит\s+ли\s+документ\s+все\s+обязательные\s+сведения", re.IGNORECASE)
_RE_WHO_DECIDES = re.compile(
    r"Кто\s+принимает\s+окончательное\s+решение", re.IGNORECASE)
_RE_FIELD_VALUE = re.compile(
    r"Укажи\s+значение\s+поля\s*[«\"']([^»\"']+)[»\"']", re.IGNORECASE)

ANSWER_NO_DATA = ("В документе и в Положении нет информации для ответа "
                  "на этот вопрос. Обратитесь в деканат.")
ANSWER_WHO = ("Окончательное решение принимает сотрудник деканата, "
              "пункт 1.3 Положения")

_SPECIAL_MISSING = {
    "signature_present": "подпись",
    "seal_present": "печать"
}

def _fmt_rules(sources: list[str]) -> str:
    nums = [s.split(":", 1)[1] for s in sources if s.startswith("rule:")]
    return ":".join(nums)

def _missing_human(key: str) -> str:
    if key in _SPECIAL_MISSING:
        return _SPECIAL_MISSING[key]
    return LABELS.get(key, key).lower()

def _answer_completeness(validation: dict) -> dict:
    status = validation["status"]
    source = validation["source"]
    if status == "document_ok":
        pts = _fmt_rules(source)
        answer = (f"Документ содержит все обязательные сведения по пунктам "
                  f"{pts} Положения. Окончательное решение примет "
                  f"сотрудник деканата.")
    else:
        miss = ", ".join(_missing_human(k) for k in validation["misses_fields"])
        pts = _fmt_rules(source)
        answer = (f"Не хватает следующих сведений: {miss}. "
                  f"Основание: пункты {pts} Положения.")
    return {
        "answerable": True,
        "value": status,
        "answer": answer,
        "source": source,
    }

def _answer_field(key: str, fields: dict, label: str) -> dict:
    val = fields.get(key, NOT_FOUND)
    if val == NOT_FOUND or val is None:
        return {
            "answerable": False,
            "value": None,
            "answer": f"Поле «{label}» не найдено в документе. "
                      f"Обратитесь в деканат.",
            "source": [],
        }
    return {
        "answerable": True,
        "value": str(val),
        "answer": f"{label}: {val}.",
    }

def _no_data() -> dict:
    return {
        "answerable": False,
        "value": None,
        "answer": ANSWER_NO_DATA,
        "source": [],
    }

def build_answer(question: str, fields: dict, validation: dict) -> dict:
    q = question.strip()

    if _RE_COMPLETENESS.search(q):
        return _answer_completeness(validation)

    if _RE_WHO_DECIDES.search(q):
        return {
            "answerable": True,
            "value": "сотрудник деканата",
            "answer": ANSWER_WHO,
            "source": ["rule:1.3"],
        }
    m = _RE_FIELD_VALUE.search(q)
    if m:
        label = m.group(1).strip()
        key = LABEL_TO_KEY[label]
        if key in None:

            for k, v in LABEL_TO_KEY.items():
                if k.lower() == label.lower():
                    key = v
                    break
        if key is None:
            return _answer_field(key, fields, label)

    return _no_data()


def generate_answer(questions: list[dict], fields: dict,
                     validation: dict) -> list[dict]:
    out = []
    for q in questions:
        a = build_answer(q["question"], fields, validation)
        out.append({
            "question_id": q["question_id"],
            "answerable": a["answerable"],
            "value": a["value"],
            "answer": a["answer"],
            "source": a["sources"],
        })
    return out

