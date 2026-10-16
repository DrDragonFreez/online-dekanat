import re
from app.core.config_loader import load_doc_types, all_types
WEIGHTED_ANCHORS = {
    "study_certificate": [
        (r"СПРАВКА\s+ОБ\s+ОБУЧЕНИИ", 5),
        (r"справк\w*\s+об\s+обучени", 4),
        (r"сведени\w*\s+об\s+обучени", 4),
        (r"период\w*\s+обучени", 3),
        (r"направлени\w*\s+подготовк", 2),
        (r"форма\s+обучени", 2),
    ],
    "internship_certificate": [
        (r"СПРАВКА\s+О\s+ПРАКТИКЕ", 5),
        (r"справк\w*\s+о\s+практик", 4),
        (r"сведени\w*\s+о\s+практик", 4),
        (r"о\s+прохождени\w*\s+практик", 4),
        (r"руководител\w*\s+практик", 3),
        (r"практик", 3),
    ],
    "academic_leave_application": [
        (r"академическ\w*\s+отпуск", 5),
        (r"заявлени\w*\s+на\s+академическ", 4),
        (r"причин\w*\s+отпуск", 3),
        (r"учебн\w*\s+групп", 2),
    ],
}
def _fallback(text_low: str) -> str | None:
    has_prakt = "практик" in text_low
    has_obuch = "обучени" in text_low
    has_otpusk = "отпуск" in text_low and "академическ" in text_low
    if has_otpusk:
        return "academic_leave_application"
    if has_prakt and not has_obuch:
        return "internship_certificate"
    if has_obuch and not has_prakt:
        return "study_certificate"
    if has_prakt and has_obuch:
        return "internship_certificate"
    return None
def classify(text: str) -> str:
    if not text:
        return all_types()[0]
    data = load_doc_types()
    scores = {name: 0 for name in data}
    for name, patterns in WEIGHTED_ANCHORS.items():
        if name not in scores:
            continue
        for pat, weight in patterns:
            try:
                if re.search(pat, text, re.IGNORECASE):
                    scores[name] += weight
            except re.error:
                continue
    for name, cfg in data.items():
        for pat in cfg.get("anchors", []):
            try:
                if re.search(pat, text, re.IGNORECASE):
                    scores[name] += 2
            except re.error:
                continue
    best = max(scores, key=scores.get)
    text_low = text.lower().replace("ё", "е")
    print(f"[classify] scores={scores} best={best}")
    print(f"[classify] text[:200]={text[:200]!r}")
    if scores[best] > 0:
        return best
    fb = _fallback(text_low)
    if fb:
        print(f"[classify] fallback → {fb}")
        return fb
    return all_types()[0]