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
            MODEL_ID,
            torch_dtype=torch.float32,
            device_map=DEVICE,
            trust_remote_code=True,
        )
        _model.eval()
        print("[LLM] Готово.")
    return _model, _tokenizer
def _build_prompt(text: str, doc_type: str) -> str:
    fields_map = {
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
    required_fields = fields_map.get(doc_type, [])
    fields_list = ", ".join(required_fields)
    return f"""Ты — ассистент деканата. Извлеки поля из текста документа.
Тип документа: {doc_type}
Нужные поля: {fields_list}

Правила:
1. Если поле не найдено в тексте — верни строго null (JSON-значение, не строку).
2. НЕ пиши "не указано", "не найдено", "нет данных". Только null.
3. Даты приводи к формату YYYY-MM-DD.
4. Не выдумывай значения — бери только из текста.
5. Верни ТОЛЬКО JSON-объект, без пояснений и markdown.

Текст документа:
\"\"\"
{text[:3000]}
\"\"\"
JSON с полями {fields_list}:
"""
def _parse_json_response(response: str, date_fields: set[str] | None = None) -> dict:
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
        "-", "—", "", "n/a", "na",
    }
    if date_fields is None:
        date_fields = set()
    from app.core.extract import normalize_date
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
        if k in date_fields:
            normalized = normalize_date(v_stripped)
            if normalized:
                out[k] = normalized
                continue
        out[k] = v_stripped
    return out
def extract_fields_llm(text: str, doc_type: str) -> dict:
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
    from app.core.config_loader import get_type
    date_fields = set(get_type(doc_type)["date_fields"])
    return _parse_json_response(response, date_fields=date_fields)