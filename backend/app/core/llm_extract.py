import json
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_NEW_TOKENS = 512
DEVICE = "cpu"
_model = None
_tokenizer = None
def _get_model():
    global _model, _tokenizer
    if _model is None:
        print(f"[LLM] Загружаю {MODEL_ID} (это займёт ~1 минуту)...")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, dtype=torch.float32, device_map=DEVICE, trust_remote_code=True,
        )
        _model.eval()
        print("[LLM] Готово.")
    return _model, _tokenizer
FIELD_DESCRIPTIONS = {
    "study_certificate": {
        "student_name": "ФИО студента полностью в именительном падеже",
        "university": "полное название учебного заведения",
        "program": "направление подготовки или специальность, обычно с кодом вроде 38.03.01",
        "study_form": "только одно из: очная, очно-заочная, заочная",
        "study_start": "дата начала обучения в формате YYYY-MM-DD",
        "study_end": "дата окончания обучения в формате YYYY-MM-DD",
        "document_number": "номер справки",
        "issue_date": "дата выдачи справки в формате YYYY-MM-DD",
    },
    "academic_leave_application": {
        "student_name": "ФИО студента полностью в именительном падеже",
        "group": "учебная группа",
        "course": "курс одной цифрой",
        "leave_reason": "причина отпуска",
        "leave_start": "дата начала отпуска в формате YYYY-MM-DD",
        "leave_end": "дата окончания отпуска в формате YYYY-MM-DD",
        "application_date": "дата подачи заявления в формате YYYY-MM-DD",
    },
    "internship_certificate": {
        "student_name": "ФИО студента полностью в именительном падеже",
        "organization": "полное название организации",
        "internship_start": "дата начала практики в формате YYYY-MM-DD",
        "internship_end": "дата окончания практики в формате YYYY-MM-DD",
        "supervisor_name": "ФИО руководителя практики полностью",
        "grade": "оценка: отлично, хорошо, удовлетворительно или зачтено",
        "document_number": "номер справки",
        "issue_date": "дата выдачи справки в формате YYYY-MM-DD",
    },
}
DATE_CONTEXT = {
    "study_start": ["начало периода обучения", "дата начала обучения", "начало обучения", "зачислен", "принят", "поступил", "приказ о зачислении"],
    "study_end": ["окончание периода обучения", "дата окончания обучения", "окончание обучения", "срок окончания", "окончит", "выпуск"],
    "issue_date": ["дата выдачи", "выдана", "выдан", "дата выдачи справки"],
    "leave_start": ["дата начала отпуска", "начало отпуска"],
    "leave_end": ["дата окончания отпуска", "окончание отпуска"],
    "application_date": ["дата заявления", "дата подачи"],
    "internship_start": ["дата начала практики", "начало практики", "период практики с"],
    "internship_end": ["дата окончания практики", "окончание практики", "период практики по"],
}
FEW_SHOT = {
    "study_certificate": """
ПРИМЕР 1. Полностью заполненная справка.
Текст: "СПРАВКА ОБ ОБУЧЕНИИ. ФИО студента: Иванов Иван Иванович. Название вуза: Учебный университет «Меридиан». Направление подготовки: 38.03.01 Экономика. Форма обучения: очная. Начало периода обучения: 01.09.2023. Окончание периода обучения: 31.08.2026. Номер справки: ОБ-1001. Дата выдачи: 01.09.2026."
Ответ: {"student_name": "Иванов Иван Иванович", "university": "Учебный университет «Меридиан»", "program": "38.03.01 Экономика", "study_form": "очная", "study_start": "2023-09-01", "study_end": "2026-08-31", "document_number": "ОБ-1001", "issue_date": "2026-09-01"}

ПРИМЕР 2. Пропущены ФИО и номер.
Текст: "Справка об обучении. ФИО студента: _______. Название вуза: Учебная академия «Горизонт». Направление подготовки: 09.03.01 Информатика. Форма обучения: очно-заочная. Номер справки: _______. Дата выдачи: 12.09.2026."
Ответ: {"student_name": null, "university": "Учебная академия «Горизонт»", "program": "09.03.01 Информатика", "study_form": "очно-заочная", "study_start": null, "study_end": null, "document_number": null, "issue_date": "2026-09-12"}

ПРИМЕР 3. ФИО в дательном падеже без метки. Даты обучения в тексте НЕТ. Не путай с датой выдачи.
Текст: "Настоящая справка дана Иванову Ивану Ивановичу в том, что он зачислен на курс повышения квалификации. № 198-81 от 12.05.2021."
Ответ: {"student_name": "Иванов Иван Иванович", "university": null, "program": null, "study_form": null, "study_start": null, "study_end": null, "document_number": "198-81", "issue_date": "2021-05-12"}

ПРИМЕР 4. Даты в формате "1 сентября 2023 года".
Текст: "ФИО студента: Крылов Артём Викторович. Название вуза: Учебный университет «Меридиан». Направление подготовки: 42.03.02 Журналистика. Форма обучения: очная. Начало периода обучения: 1 сентября 2023 года. Окончание периода обучения: 31 августа 2026 года. Номер справки: ОБ-1008. Дата выдачи: 14 сентября 2026 года."
Ответ: {"student_name": "Крылов Артём Викторович", "university": "Учебный университет «Меридиан»", "program": "42.03.02 Журналистика", "study_form": "очная", "study_start": "2023-09-01", "study_end": "2026-08-31", "document_number": "ОБ-1008", "issue_date": "2026-09-14"}

ПРИМЕР 5. Только дата выдачи, дат обучения нет.
Текст: "Настоящая справка дана Иванову Ивану Ивановичу. Зачислен на курс повышения квалификации «Название курса». № 198-81 от 12.05.2021."
Ответ: {"student_name": "Иванов Иван Иванович", "university": null, "program": null, "study_form": null, "study_start": null, "study_end": null, "document_number": "198-81", "issue_date": "2021-05-12"}
""",
    "academic_leave_application": """
ПРИМЕР 1. Полностью заполненное заявление.
Текст: "ЗАЯВЛЕНИЕ НА АКАДЕМИЧЕСКИЙ ОТПУСК. ФИО студента: Соколов Олег Николаевич. Учебная группа: ЖР-25-1. Курс: 3. Причина отпуска: по состоянию здоровья. Дата начала отпуска: 1 ноября 2026 года. Дата окончания отпуска: 31 августа 2027 года. Дата заявления: 7 октября 2026 года."
Ответ: {"student_name": "Соколов Олег Николаевич", "group": "ЖР-25-1", "course": "3", "leave_reason": "по состоянию здоровья", "leave_start": "2026-11-01", "leave_end": "2027-08-31", "application_date": "2026-10-07"}

ПРИМЕР 2. Пропущена дата заявления.
Текст: "ЗАЯВЛЕНИЕ НА АКАДЕМИЧЕСКИЙ ОТПУСК. ФИО студента: Павлов Фёдор Дмитриевич. Учебная группа: ЭК-24-2. Курс: 4. Причина отпуска: по семейным обстоятельствам. Дата начала отпуска: 01.11.2026. Дата окончания отпуска: 31.08.2027. Дата заявления: _______."
Ответ: {"student_name": "Павлов Фёдор Дмитриевич", "group": "ЭК-24-2", "course": "4", "leave_reason": "по семейным обстоятельствам", "leave_start": "2026-11-01", "leave_end": "2027-08-31", "application_date": null}

ПРИМЕР 3. Пропущена причина отпуска.
Текст: "ЗАЯВЛЕНИЕ НА АКАДЕМИЧЕСКИЙ ОТПУСК. ФИО студента: Орлов Фёдор Викторович. Учебная группа: ЖР-22-3. Курс: 2. Причина отпуска: _______. Дата начала отпуска: 01.11.2026. Дата окончания отпуска: 31.08.2027. Дата заявления: 09.10.2026."
Ответ: {"student_name": "Орлов Фёдор Викторович", "group": "ЖР-22-3", "course": "2", "leave_reason": null, "leave_start": "2026-11-01", "leave_end": "2027-08-31", "application_date": "2026-10-09"}

ПРИМЕР 4. Пропущены группа и курс.
Текст: "ЗАЯВЛЕНИЕ НА АКАДЕМИЧЕСКИЙ ОТПУСК. ФИО студента: Иванов Борис Николаевич. Учебная группа: ________. Курс: _______. Причина отпуска: по семейным обстоятельствам. Дата начала отпуска: 01.11.2026. Дата окончания отпуска: 31.08.2027. Дата заявления: 05.10.2026."
Ответ: {"student_name": "Иванов Борис Николаевич", "group": null, "course": null, "leave_reason": "по семейным обстоятельствам", "leave_start": "2026-11-01", "leave_end": "2027-08-31", "application_date": "2026-10-05"}

ПРИМЕР 5. Пропущено ФИО.
Текст: "ЗАЯВЛЕНИЕ НА АКАДЕМИЧЕСКИЙ ОТПУСК. ФИО студента: _______. Учебная группа: ИВТ-23-4. Курс: 4. Причина отпуска: в связи с уходом за родственником. Дата начала отпуска: 1 ноября 2026 года. Дата окончания отпуска: 31 августа 2027 года. Дата заявления: 6 октября 2026 года."
Ответ: {"student_name": null, "group": "ИВТ-23-4", "course": "4", "leave_reason": "в связи с уходом за родственником", "leave_start": "2026-11-01", "leave_end": "2027-08-31", "application_date": "2026-10-06"}
""",
    "internship_certificate": """
ПРИМЕР 1. Полностью заполненная справка.
Текст: "СПРАВКА О ПРАКТИКЕ. ФИО студента: Данилов Олег Алексеевич. Название организации: Учебная организация «Спектр». Дата начала практики: 01.06.2026. Дата окончания практики: 15.07.2026. ФИО руководителя практики: Ильина Елена Андреевна. Оценка: удовлетворительно. Номер справки: ПР-2021. Дата выдачи: 18.07.2026."
Ответ: {"student_name": "Данилов Олег Алексеевич", "organization": "Учебная организация «Спектр»", "internship_start": "2026-06-01", "internship_end": "2026-07-15", "supervisor_name": "Ильина Елена Андреевна", "grade": "удовлетворительно", "document_number": "ПР-2021", "issue_date": "2026-07-18"}

ПРИМЕР 2. Пропущена дата выдачи.
Текст: "СПРАВКА О ПРАКТИКЕ. ФИО студента: Мельников Фёдор Михайлович. Название организации: Учебная организация «Спектр». Дата начала практики: 1 июня 2026 года. Дата окончания практики: 15 июля 2026 года. ФИО руководителя практики: Соколова Анна Викторовна. Оценка: зачтено. Номер справки: ПР-2022. Дата выдачи: _______."
Ответ: {"student_name": "Мельников Фёдор Михайлович", "organization": "Учебная организация «Спектр»", "internship_start": "2026-06-01", "internship_end": "2026-07-15", "supervisor_name": "Соколова Анна Викторовна", "grade": "зачтено", "document_number": "ПР-2022", "issue_date": null}

ПРИМЕР 3. Пропущены руководитель и оценка.
Текст: "СПРАВКА О ПРАКТИКЕ. ФИО студента: Смирнов Кирилл Сергеевич. Название организации: Учебная организация «Парус». Дата начала практики: 01.06.2026. Дата окончания практики: 15.07.2026. ФИО руководителя практики: _______. Оценка: _______. Номер справки: ПР-2027. Дата выдачи: 25.07.2026."
Ответ: {"student_name": "Смирнов Кирилл Сергеевич", "organization": "Учебная организация «Парус»", "internship_start": "2026-06-01", "internship_end": "2026-07-15", "supervisor_name": null, "grade": null, "document_number": "ПР-2027", "issue_date": "2026-07-25"}

ПРИМЕР 4. Пропущены организация и начало практики.
Текст: "СПРАВКА О ПРАКТИКЕ. ФИО студента: Семенов Илья Дмитриевич. Название организации: ________. Дата начала практики: ________. Дата окончания практики: 15 июля 2026 года. ФИО руководителя практики: Соколова Анна Викторовна. Оценка: удовлетворительно. Номер справки: ПР-2026. Дата выдачи: 23 июля 2026 года."
Ответ: {"student_name": "Семенов Илья Дмитриевич", "organization": null, "internship_start": null, "internship_end": "2026-07-15", "supervisor_name": "Соколова Анна Викторовна", "grade": "удовлетворительно", "document_number": "ПР-2026", "issue_date": "2026-07-23"}
""",
}
def _get_type_config(doc_type):
    try:
        from backend.app.core.config_loader import get_type
        return get_type(doc_type)
    except Exception:
        return None


_FALLBACK_FIELDS_MAP = {
    "study_certificate": [
        "student_name", "university", "program", "study_form",
        "study_start", "study_end", "document_number", "issue_date",
    ],
    "academic_leave_application": [
        "student_name", "group", "course", "leave_reason",
        "leave_start", "leave_end", "application_date",
    ],
    "internship_certificate": [
        "student_name", "organization", "internship_start",
        "internship_end", "supervisor_name", "grade",
        "document_number", "issue_date",
    ],
}
def _build_prompt(text, doc_type):
    cfg = _get_type_config(doc_type)
    llm_cfg = (cfg or {}).get("llm", {}) or {}

    if llm_cfg.get("fields"):
        required_fields = list(llm_cfg["fields"])
    else:
        required_fields = _FALLBACK_FIELDS_MAP.get(doc_type, [])

    if llm_cfg.get("fields_description"):
        desc = llm_cfg["fields_description"]
    else:
        desc = FIELD_DESCRIPTIONS.get(doc_type, {})

    if llm_cfg.get("few_shot"):
        few_shot = llm_cfg["few_shot"]
    else:
        few_shot = FEW_SHOT.get(doc_type, "")

    fields_list = ", ".join(required_fields)
    fields_desc = "\n".join(f"  - {k}: {desc.get(k, k)}" for k in required_fields)
    return f"""Ты — ассистент деканата. Извлекаешь поля из текста студенческого документа.

Тип документа: {doc_type}
Нужные поля: {fields_list}

Описание полей:
{fields_desc}

ПРАВИЛА:
1. Если поле не найдено — верни null (JSON null, не строку).
2. НИКОГДА не пиши "не найдено", "не указано", "нет данных". Только null.
3. Даты всегда в формате YYYY-MM-DD. Форматы на входе: "01.09.2023", "1 сентября 2023 года", "2023-09-01".
4. Бери значения из строк "Метка: значение". Если метки нет, но значение очевидно — бери его.
5. ФИО может стоять БЕЗ метки, внутри предложения: "справка дана Иванову Ивану Ивановичу". ВСЕГДА возвращай ФИО в ИМЕНИТЕЛЬНОМ падеже: "Иванов Иван Иванович".
6. Номер и дату справки бери из шапки, если они в форме "№ XXXX-NN от DD.MM.YYYY". НЕ бери лицензию, свидетельство, ОГРН, ИНН, КПП, номер приказа.
7. Placeholder — пустое место под заполнение. Примеры: "Название курса", "Дата", "Подпись", "ФИО", "___", "«Название»". Верни null.
8. Если после метки идёт другая метка — пустое поле, верни null.
9. study_form — только "очная", "очно-заочная" или "заочная".
10. ГЛАВНОЕ: НЕ ставь одну и ту же дату в разные поля. study_start — это дата НАЧАЛА ОБУЧЕНИЯ (зачисление), study_end — дата ОКОНЧАНИЯ ОБУЧЕНИЯ. issue_date — дата ВЫДАЧИ справки. Это РАЗНЫЕ даты. Если подходящей даты в тексте нет — null.
11. Отвечай ТОЛЬКО JSON-объектом, без markdown, без ```json.

Примеры:
{few_shot}

Теперь твой документ:
\"\"\"
{text[:3000]}
\"\"\"

Верни JSON с полями: {fields_list}"""
_PLACEHOLDER_PATTERNS = [
    re.compile(r"^название\s+(курса|программы|организации|документа|вуза|университета|учебного|подразделения|специальности|направления)$", re.I),
    re.compile(r"^дата$", re.I),
    re.compile(r"^подпись$", re.I),
    re.compile(r"^фио$", re.I),
    re.compile(r"^оценка$", re.I),
    re.compile(r"^номер$", re.I),
    re.compile(r"^группа$", re.I),
    re.compile(r"^курс$", re.I),
    re.compile(r"^_{2,}$"),
    re.compile(r"^\.{2,}$"),
    re.compile(r"^-{2,}$"),
    re.compile(r"^«[^»]{0,5}»$"),
    re.compile(r"^<[^>]{0,30}>$"),
    re.compile(r"^\[.+\]$"),
    re.compile(r"^x+$", re.I),
    re.compile(r"^n/?a$", re.I),
]
def _is_placeholder(value):
    v = value.strip()
    if not v:
        return True
    v_no_quotes = v.strip("«»\"'“”„").strip()
    if len(v_no_quotes) <= 3 and not v_no_quotes.isdigit():
        return True
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.match(v_no_quotes) or pat.match(v):
            return True
    return False
def _normalize_for_search(s):
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[«»\"'“”„]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()
_MONTHS_FOR_SEARCH = {
    "01": "января", "02": "февраля", "03": "марта", "04": "апреля",
    "05": "мая", "06": "июня", "07": "июля", "08": "августа",
    "09": "сентября", "10": "октября", "11": "ноября", "12": "декабря",
}
_RE_DOCNUM_DATE = re.compile(
    r"(?:№|N[oо°º]?|#)\s*[А-ЯЁA-Z0-9\-/]+\s+от\s+"
    r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})",
    re.IGNORECASE,
)
def _find_date_positions(value, text_norm):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", value)
    if not m:
        return []
    y, mo, d = m.group(1), m.group(2), m.group(3)
    d_int = str(int(d))
    mo_int = str(int(mo))
    variants = [
        f"{d}.{mo}.{y}",
        f"{d_int}.{mo_int}.{y}",
        f"{y}-{mo}-{d}",
        f"{d}/{mo}/{y}",
        f"{d_int}/{mo_int}/{y}",
    ]
    month = _MONTHS_FOR_SEARCH.get(mo)
    if month:
        variants.append(f"{d} {month} {y}")
        variants.append(f"{d_int} {month} {y}")
    positions = []
    for v in variants:
        start = 0
        while True:
            idx = text_norm.find(v, start)
            if idx == -1:
                break
            positions.append((idx, idx + len(v)))
            start = idx + 1
    return positions
def _matches_docnum_date(value, text_norm):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", value)
    if not m:
        return False
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    for mm in _RE_DOCNUM_DATE.finditer(text_norm):
        dd = int(mm.group(1))
        moo = int(mm.group(2))
        yy = int(mm.group(3))
        if yy < 100:
            yy += 2000 if yy < 50 else 1900
        if (dd, moo, yy) == (d, mo, y):
            return True
    return False
def _check_date_context(value, key, text):
    context_words = DATE_CONTEXT.get(key)
    if not context_words:
        return True
    text_norm = _normalize_for_search(text)
    if key == "issue_date" and _matches_docnum_date(value, text_norm):
        return True
    positions = _find_date_positions(value, text_norm)
    if not positions:
        return False
    window = 120
    for start, end in positions:
        left = text_norm[max(0, start - window): start]
        right = text_norm[end: end + window]
        around = left + " " + right
        for word in context_words:
            if word in around:
                return True
    return False
def _verify_value_in_text(value, key, text, date_fields):
    if not value or value == "не найдено":
        return False
    text_norm = _normalize_for_search(text)
    val_norm = _normalize_for_search(value)
    if not val_norm:
        return False
    if key in date_fields:
        return _check_date_context(value, key, text)
    return val_norm in text_norm
def _verify_name_in_text(name, text):
    if not name:
        return False
    text_norm = _normalize_for_search(text)
    words = name.split()
    if not words:
        return False
    surname = words[0].lower().replace("ё", "е")
    if len(surname) < 3:
        return False
    stem_len = min(5, len(surname) - 1) if len(surname) > 5 else len(surname)
    stem = surname[:max(4, stem_len)]
    if len(stem) < 3:
        stem = surname[:3]
    return stem in text_norm
def _parse_json_response(response, date_fields=None):
    m = re.search(r"\{.*\}", response, re.DOTALL)
    if not m:
        return {}
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError:
        return {}
    NOT_FOUND_WORDS = {
        "не найдено", "не указано", "не указан", "не указана",
        "не указаны", "нет", "нет данных", "null", "none", "отсутствует",
        "-", "—", "", "n/a", "na", "null ",
    }
    if date_fields is None:
        date_fields = set()
    from backend.app.core.extract import normalize_date
    out = {}
    for k, v in data.items():
        if v is None:
            out[k] = "не найдено"
            continue
        if isinstance(v, (int, float)):
            v = str(v)
        if not isinstance(v, str):
            out[k] = "не найдено"
            continue
        v_stripped = v.strip()
        if v_stripped.lower() in NOT_FOUND_WORDS:
            out[k] = "не найдено"
            continue
        if k == "study_form":
            match = re.search(r"(очно-заочная|очная|заочная)", v_stripped.lower())
            if match:
                out[k] = match.group(1)
                continue
            out[k] = "не найдено"
            continue
        if k == "course":
            m = re.search(r"\d+", v_stripped)
            if m:
                out[k] = m.group(0)
                continue
            out[k] = "не найдено"
            continue
        if k in ("grade",):
            v_low = v_stripped.lower()
            found = None
            for valid in ("отлично", "хорошо", "удовлетворительно", "неудовлетворительно", "зачтено", "не зачтено"):
                if valid in v_low:
                    found = valid
                    break
            out[k] = found if found else v_stripped
            continue
        if _is_placeholder(v_stripped):
            out[k] = "не найдено"
            continue
        if k in date_fields:
            normalized = normalize_date(v_stripped)
            if normalized:
                out[k] = normalized
                continue
        out[k] = v_stripped
    return out
def _name_fields_for(doc_type):
    cfg = _get_type_config(doc_type)
    if cfg and cfg.get("name_fields"):
        return set(cfg["name_fields"])
    return {"student_name", "supervisor_name"}
def extract_fields_llm(text, doc_type):
    model, tokenizer = _get_model()
    prompt = _build_prompt(text, doc_type)
    messages = [
        {"role": "system", "content": "Ты — точный извлекатель данных. Отвечай только JSON."},
        {"role": "user", "content": prompt},
    ]
    encoded = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    )
    input_ids = encoded["input_ids"].to(DEVICE)
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = outputs[0][input_ids.shape[1]:]
    response = tokenizer.decode(generated, skip_special_tokens=True).strip()
    from backend.app.core.config_loader import get_type
    date_fields = set(get_type(doc_type)["date_fields"])
    name_fields = _name_fields_for(doc_type)
    parsed = _parse_json_response(response, date_fields=date_fields)
    verified = {}
    for k, v in parsed.items():
        if v == "не найдено":
            verified[k] = v
            continue
        if k in name_fields:
            if _verify_name_in_text(v, text):
                verified[k] = v
            else:
                print(f"[LLM] отброшено имя (нет корня в тексте): {k} = {v!r}")
                verified[k] = "не найдено"
            continue
        if _verify_value_in_text(v, k, text, date_fields):
            verified[k] = v
        else:
            print(f"[LLM] отброшено (нет контекста): {k} = {v!r}")
            verified[k] = "не найдено"
    return verified