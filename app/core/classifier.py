import re

ANCHORS = {
    "study_certificate": [
        r"СПРАВКА\s+ОБ\s+ОБУЧЕНИЕ"
        r"Сведения\s+об\s+обучение\s+студента",
    ],
    "academic_leave_application": [
        r"ЗАЯВЛЕНИЕ\s+НА\s+АКАДЕМИЧЕСКИЙ\s+ОТПУСк"
        r"Прошу\s+предоставить\s+академический\s+отпуск",
    ],
    "internship_certificate": [
        r"СПРАВКА\s+О\s+ПРАКТИКЕ"
        r"Сведения\s+о\s+практике",
    ],
}

def classify(text: str) -> str:
    scores = {k: 0 for k in ANCHORS}
    for dtype, pats in ANCHORS.items():
        for p in pats:
            if re.search(p, text, re.IGNORECASE):
                scores[dtype] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "study_certificate"

