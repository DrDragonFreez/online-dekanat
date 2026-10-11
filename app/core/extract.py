import re

from app.core.text_post import fix_quotes

NOT_FOUND = "не найдено"

_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

_DATE_DDMMYYYY = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})")
_DATE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_DATE_LONG = re.compile(r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})", re.IGNORECASE)


def normalize_date(s: str):
    s = s.strip()
    if not s:
        return None
    m = _DATE_DDMMYYYY.search(s)
    if m:
        d, mo, y = int(m.group(1)), m.group(2), int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = _DATE_LONG.search(s)
    if m:
        d, mon, y = int(m.group(1)), _MONTHS.get(m.group(2).lower()), int(m.group(3))
        if mon:
            return f"{y:04d}-{mon:02d}-{d:02d}"
    m = _DATE_ISO.search(s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


FIELD_ORDER = {
    "study_certificate": [

        "student_name", "university", "program", "study_form",
        "study_start", "study_end", "document_number", "issue_date",
        "signature_present", "seal_present",
    ],
    "academic_leave_application": [
        "student_name", "group", "course", "leave_reason",
        "leave_start", "leave_end", "application_date", "signature_present",
    ],
    "internship_certificate": [
        "student_name", "organization", "internship_star", "internship_end",
        "supervisor_name", "grade", "document_number", "issue_date",
        "signature_present", "seal_present",
    ],
}

LABELS = {
    "student_name": "ФИО студента",
    "university": "Название вуза",
    "program": "Направления подготовки",
    "study_form": "форма обучения",
    "study_start": "Начало периода обучения",
    "study_end": "Окончание периода обучения",
    "document_number": "Номер справки",
    "issue_date": "Дата выдачи",
    "group": "Учебная группа",
    "course": "Курс",
    "leave_reason": "Причина отпуска",
    "leave_start": "Дата начала отпуска",
    "leave_end": "Дата окончания отпуска",
    "application_date": "Дата заявления",
    "organization": "Название организации",
    "internship_start": "Дата начала практики",
    "internship_end": "Дата окончания практики",
    "supervisor_name": "ФИО руководителя практики",
    "grade": "Оценка",
}

LABEL_TO_KEY = {v: k for k, v in LABELS.items()}

TEXT_FIELDS_BY_TYPE = {
    "study_certificate": [
        "student_name", "university", "program", "study_form",
        "study_start", "study_end", "document_number", "issue_date",
    ],
    "academic_leave_application": [
        "student_name", "group", "course", "leave_reason",
        "leave_start", "leave_end", "application_date",
    ],
    "internship_certificate": [
        "student_name", "organization", "internship_star", "internship_end",
        "supervisor_name", "grade", "document_number", "issue_date",
    ],
}

DATE_FIELDS = {
    "study_start", "study_end", "issue_date",
    "leave_start", "leave_end", "application_date",
    "internship_start", "internship_end",
}

_UNDERSCORES = re.compile(r"[_\s]+$")


def _clean_value(raw: str) -> str:
    raw = raw.strip()
    raw = _UNDERSCORES.sub("", raw).strip()
    raw = raw.rstrip(".").strip()
    return raw


def extract_fields(text: str, doc_type: str) -> dict:
    if doc_type not in TEXT_FIELDS_BY_TYPE:
        raise ValueError(f"Неизвестный тип документа: {doc_type}")

    keys = TEXT_FIELDS_BY_TYPE[doc_type]
    fields: dict = {}
    lines = [l.rstrip() for l in text.splitlines()]

    for key in keys:
        label = LABELS[key]
        pat = re.compile(rf"^{re.escape(label)}\s*:\s*(.*)$")
        value = None
        for line in lines:
            m = pat.match(line)
            if m:
                raw = _clean_value(m.group(1))
                if raw:
                    value = raw
                break

        if value is None:
            fields[key] = NOT_FOUND
        elif key in DATE_FIELDS:
            nd = normalize_date(value)
            fields[key] = nd if nd else value
        else:
            fields[key] = value

    for k in ("university", "organization"):
        if fields.get(k) and fields[k] != NOT_FOUND:
            fields[k] = fix_quotes(fields[k])

    if "signature_present" in FIELD_ORDER[doc_type]:
        fields["signature_present"] = False
    if "seal_present" in FIELD_ORDER[doc_type]:
        fields["seal_present"] = False

    return {k: fields[k] for k in FIELD_ORDER[doc_type]}
