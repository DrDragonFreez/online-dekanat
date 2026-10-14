import re
_LAT_TO_CYR = {
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М",
    "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У",
    "a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у",
}
_MULTI_SPACE = re.compile(r"[ \t\u00A0]{2,}")
def _replace_latin(text: str) -> str:
    return "".join(_LAT_TO_CYR.get(ch, ch) for ch in text)
def normalize(text: str) -> str:
    text = _replace_latin(text)
    text = _MULTI_SPACE.sub(" ", text)
    text = re.sub(r"\s+([:;,.])(?!\d)", r"\1", text)
    return text