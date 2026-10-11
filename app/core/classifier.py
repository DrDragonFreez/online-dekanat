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

