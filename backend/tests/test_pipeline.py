import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.app.core.extract import extract_fields, normalize_date, NOT_FOUND
from backend.app.core.rules import validate
from backend.app.core.answers import build_answer
def test_normalize_date_dot():
    assert normalize_date("01.09.2023") == "2023-09-01"
    assert normalize_date("31.08.2026") == "2026-08-31"
    assert normalize_date("7.10.2026") == "2026-10-07"
def test_normalize_date_long():
    assert normalize_date("1 сентября 2022 года") == "2022-09-01"
    assert normalize_date("31 августа 2026 года") == "2026-08-31"
    assert normalize_date("7 октября 2026 года") == "2026-10-07"
def test_normalize_date_iso():
    assert normalize_date("2026-09-01") == "2026-09-01"
def test_normalize_date_garbage():
    assert normalize_date("не дата") is None
    assert normalize_date("") is None
SAMPLE_STUDY = """ФИО студента: Александров Артём Игоревич
Название вуза: Учебный университет «Меридиан»
Направление подготовки: 38.03.01 Экономика
Форма обучения: очная
Начало периода обучения: 01.09.2023
Окончание периода обучения: 31.08.2026
Номер справки: ОБ-1001
Дата выдачи: 01.09.2026"""
def test_extract_study_certificate():
    f = extract_fields(SAMPLE_STUDY, "study_certificate")
    assert f["student_name"] == "Александров Артём Игоревич"
    assert f["university"] == "Учебный университет «Меридиан»"
    assert f["program"] == "38.03.01 Экономика"
    assert f["study_form"] == "очная"
    assert f["study_start"] == "2023-09-01"
    assert f["study_end"] == "2026-08-31"
    assert f["document_number"] == "ОБ-1001"
    assert f["issue_date"] == "2026-09-01"
SAMPLE_STUDY_MISSING = """ФИО студента: Мельников Денис Игоревич
Название вуза: Учебная академия «Горизонт»
Направление подготовки: 09.03.01 Информатика и вычислительная техника
Форма обучения: очно-заочная
Начало периода обучения: 1 сентября 2022 года
Окончание периода обучения: 31 августа 2026 года
Номер справки: ОБ-1002
Дата выдачи: __________________________"""
def test_extract_missing_date():
    f = extract_fields(SAMPLE_STUDY_MISSING, "study_certificate")
    assert f["issue_date"] == NOT_FOUND
    assert f["student_name"] == "Мельников Денис Игоревич"
    assert f["study_start"] == "2022-09-01"
SAMPLE_LEAVE = """ФИО студента: Соколов Олег Николаевич
Учебная группа: ЖР-25-1
Курс: 3
Причина отпуска: по состоянию здоровья
Дата начала отпуска: 1 ноября 2026 года
Дата окончания отпуска: 31 августа 2027 года
Дата заявления: 7 октября 2026 года"""
def test_extract_academic_leave():
    f = extract_fields(SAMPLE_LEAVE, "academic_leave_application")
    assert f["student_name"] == "Соколов Олег Николаевич"
    assert f["group"] == "ЖР-25-1"
    assert f["course"] == "3"
    assert f["leave_reason"] == "по состоянию здоровья"
    assert f["leave_start"] == "2026-11-01"
    assert f["leave_end"] == "2027-08-31"
    assert f["application_date"] == "2026-10-07"
def test_validate_complete():
    f = extract_fields(SAMPLE_STUDY, "study_certificate")
    f["signature_present"] = True
    f["seal_present"] = True
    v = validate(f, "study_certificate")
    assert v["status"] == "document_ok"
    assert v["missing_fields"] == []
    assert v["sources"] == ["rule:3.1", "rule:3.2", "rule:3.3"]
def test_validate_missing_field():
    f = extract_fields(SAMPLE_STUDY_MISSING, "study_certificate")
    f["signature_present"] = True
    f["seal_present"] = True
    v = validate(f, "study_certificate")
    assert v["status"] == "missing_fields"
    assert v["missing_fields"] == ["issue_date"]
    assert v["sources"] == ["rule:3.1"]
def test_validate_missing_flag():
    f = extract_fields(SAMPLE_STUDY, "study_certificate")
    f["signature_present"] = False
    f["seal_present"] = True
    v = validate(f, "study_certificate")
    assert v["status"] == "missing_fields"
    assert v["missing_fields"] == ["signature_present"]
    assert v["sources"] == ["rule:3.2"]
def test_answer_completeness_ok():
    f = extract_fields(SAMPLE_STUDY, "study_certificate")
    f["signature_present"] = True
    f["seal_present"] = True
    v = validate(f, "study_certificate")
    a = build_answer(
        "Содержит ли документ все обязательные сведения по Положению?",
        f, v)
    assert a["answerable"] is True
    assert a["value"] == "document_ok"
    assert a["sources"] == ["rule:3.1", "rule:3.2", "rule:3.3"]
def test_answer_completeness_missing():
    f = extract_fields(SAMPLE_STUDY_MISSING, "study_certificate")
    f["signature_present"] = True
    f["seal_present"] = True
    v = validate(f, "study_certificate")
    a = build_answer(
        "Содержит ли документ все обязательные сведения по Положению?",
        f, v)
    assert a["value"] == "missing_fields"
    assert a["sources"] == ["rule:3.1"]
def test_answer_field():
    f = extract_fields(SAMPLE_STUDY, "study_certificate")
    f["signature_present"] = True
    f["seal_present"] = True
    v = validate(f, "study_certificate")
    a = build_answer("Укажи значение поля «ФИО студента».", f, v)
    assert a["answerable"] is True
    assert a["value"] == "Александров Артём Игоревич"
    assert a["sources"] == ["field:student_name"]
def test_answer_field_missing():
    f = extract_fields(SAMPLE_STUDY_MISSING, "study_certificate")
    f["signature_present"] = True
    f["seal_present"] = True
    v = validate(f, "study_certificate")
    a = build_answer("Укажи значение поля «Дата выдачи».", f, v)
    assert a["answerable"] is False
    assert a["value"] is None
    assert a["sources"] == []
def test_answer_who_decides():
    a = build_answer(
        "Кто принимает окончательное решение о принятии документа?",
        {}, {"status": "document_ok", "missing_fields": [], "sources": []})
    assert a["answerable"] is True
    assert a["value"] == "сотрудник деканата"
    assert a["sources"] == ["rule:1.3"]
def test_answer_no_data():
    a = build_answer(
        "Какова стоимость обучения за следующий семестр?",
        {}, {"status": "document_ok", "missing_fields": [], "sources": []})
    assert a["answerable"] is False
    assert a["value"] is None
    assert a["sources"] == []