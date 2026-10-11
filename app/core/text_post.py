import re
_ORG_PATTERNS = [
    (re.compile(
        r"(Учебный\s+университет)\s*[«\"'“(]?\s*([А-ЯЁ][а-яё]+)\s*[»\"'”)]?",
        re.IGNORECASE), r"\1 «\2»"),
    (re.compile(
        r"(Учебная\s+академия)\s*[«\"'“(]?\s*([А-ЯЁ][а-яё]+)\s*[»\"'”)]?",
        re.IGNORECASE), r"\1 «\2»"),
    (re.compile(
        r"(Учебный\s+институт)\s*[«\"'“(]?\s*([А-ЯЁ][а-яё]+)\s*[»\"'”)]?",
        re.IGNORECASE), r"\1 «\2»"),
    (re.compile(
        r"(Учебная\s+организация)\s*[«\"'“(]?\s*([А-ЯЁ][а-яё]+)\s*[»\"'”)]?",
        re.IGNORECASE), r"\1 «\2»"),
]
def fix_quotes(text: str) -> str:
    for pat, repl in _ORG_PATTERNS:
        text = pat.sub(repl, text)
    return text
def fix_spaces(text: str) -> str:
    text = re.sub(r"(\d)([А-ЯЁа-яё])", r"\1 \2", text)  # 1сентября → 1 сентября
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text
def postprocess(text: str) -> str:
    return fix_spaces(fix_quotes(text))