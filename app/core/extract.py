import re
from app.core.text_post import fix_quotes
from app.core.config_loader import get_type, load_doc_types
from app.core.patterns import (
    PATTERNS,
    LABEL_SYNONYMS,
    normalize_label,
)
NOT_FOUND = "не найдено"
_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11,
    "декабря": 12,
}
_DATE_DDMMYYYY = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})")
_DATE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_DATE_LONG = re.compile(r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})", re.IGNORECASE)
def normalize_date(s):
    if not s:
        return None
    s = s.strip()
    m = _DATE_DDMMYYYY.search(s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = _DATE_LONG.search(s)
    if m:
        d = int(m.group(1))
        mon = _MONTHS.get(m.group(2).lower())
        y = int(m.group(3))
        if mon:
            return f"{y:04d}-{mon:02d}-{d:02d}"
    m = _DATE_ISO.search(s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None
def _build_lookup():
    data = load_doc_types()
    labels = {}
    order = {}
    text = {}
    dates = {}
    for name, cfg in data.items():
        order[name] = list(cfg["fields_order"])
        text[name] = list(cfg["text_fields"])
        dates[name] = set(cfg["date_fields"])
        for key, lbl in cfg["labels"].items():
            labels.setdefault(key, lbl)
    return labels, order, text, dates
LABELS, FIELD_ORDER, TEXT_FIELDS_BY_TYPE, DATE_FIELDS = _build_lookup()
LABEL_TO_KEY = {v: k for k, v in LABELS.items()}
def _clean_value(raw):
    if raw is None:
        return ""
    raw = raw.strip()
    raw = raw.strip("_").strip()
    raw = raw.rstrip(".").strip()
    return raw
def _pattern_match(text, key, cfg=None):
    pats = []
    if cfg is not None:
        pats = (cfg.get("patterns") or {}).get(key) or []
    if not pats:
        pats = PATTERNS.get(key, [])
    for pat in pats:
        try:
            m = re.search(pat, text, re.IGNORECASE)
            if m and m.groups():
                value = _clean_value(m.group(1))
                if value and 1 < len(value) < 200:
                    if "\n" in value:
                        continue
                    return value
        except re.error:
            continue
    return None
def extract_fields(text, doc_type):
    cfg = get_type(doc_type)
    labels = cfg["labels"]
    text_fields = cfg["text_fields"]
    order = cfg["fields_order"]
    date_fields = set(cfg["date_fields"])
    lines = [l.rstrip() for l in text.splitlines()]
    fields = {}
    doc_labels = {}
    label_pat = re.compile(r"^(.+?)\s*[:\-]\s*(.*)$")
    for i, line in enumerate(lines):
        m = label_pat.match(line)
        if not m:
            continue
        left = _clean_value(m.group(1))
        right = _clean_value(m.group(2))
        if not left:
            continue
        norm = normalize_label(left)
        if norm not in doc_labels:
            doc_labels[norm] = right
    for key in text_fields:
        value = None
        found_label = False
        candidates = [labels[key], *LABEL_SYNONYMS.get(key, [])]
        seen = set()
        for candidate in candidates:
            norm = normalize_label(candidate)
            if norm in seen:
                continue
            seen.add(norm)
            if norm in doc_labels:
                found_label = True
                right = doc_labels[norm]
                if right:
                    value = right
                break
        if not found_label:
            value = _pattern_match(text, key, cfg)
        if value is None or value == "":
            fields[key] = NOT_FOUND
        elif key in date_fields:
            nd = normalize_date(value)
            fields[key] = nd if nd else value
        else:
            fields[key] = value
    for k in ("university", "organization"):
        if fields.get(k) and fields[k] != NOT_FOUND:
            fields[k] = fix_quotes(fields[k])
    if "signature_present" in order:
        fields["signature_present"] = False
    if "seal_present" in order:
        fields["seal_present"] = False
    return {k: fields[k] for k in order}