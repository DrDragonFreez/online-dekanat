# 🎓Деканыч

Цифровой секретарь: читает фото или скан студенческого документа,
проверяет его по Положению и отвечает на вопросы со ссылкой на пункт.

---

## Что умеет

- **Читает PDF и изображения.** PDF с текстовым слоем — через `pdfplumber`,
  скан и PNG/JPG — через Tesseract (русский язык).
- **Определяет тип документа** автоматически: справка об обучении,
  заявление на академический отпуск, справка о практике.
- **Извлекает 8–10 полей** на тип документа, даты приводит к ISO
  `YYYY-MM-DD`, кавычки — к «ёлочкам».
- **Проверяет комплектность** по Положению и называет пропущенные
  пункты: `rule:3.1`, `rule:3.2`, `rule:3.3`.
- **Находит подпись и печать** — по позиции изображений в PDF или
  по синему цвету в PNG.
- **Отвечает на 4 типа вопросов:** комплектность, значение поля,
  кто принимает решение, нет данных.
- **REST API + Swagger** на `/docs` и тёмный UI на `/`.

---

## Быстрый старт

### 1. Зависимости Python

```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Tesseract (OCR)

Tesseract — системный бинарь, через pip его не поставить.

**Ubuntu / Debian:**
```bash
sudo apt install tesseract-ocr tesseract-ocr-rus
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
1. Скачать установщик: https://github.com/UB-Mannheim/tesseract/wiki
2. При установке выбрать **Additional language data → Russian**.
3. В `backend/app` раскомментировать:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
   os.environ.setdefault("TESSDATA_PREFIX", r"C:\Program Files\Tesseract-OCR\tessdata")
   ```

Проверка:
```bash
tesseract --version
tesseract --list-langs | grep rus
```

### 3. Запуск

```bash
uvicorn app.main:app --reload
```

- UI: http://127.0.0.1:8000/
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

---

## Как это работает

```
    PDF / PNG
        │
        ▼
 ┌──────────────┐
 │ PDF / OCR    │  pdfplumber → текст
 │              │  Tesseract  → текст
 │              │  OpenCV     → подпись, печать
 └──────┬───────┘
        │  plain text + 2 флага
        ▼
 ┌──────────────┐
 │ Классификатор│  справка / заявление / практика
 └──────┬───────┘
        ▼
 ┌──────────────┐
 │  Извлечение  │  8–10 полей, даты → ISO
 └──────┬───────┘
        ▼
 ┌──────────────┐
 │   Правила    │  Положение п. 1.3, 3.1–3.3, 4.1–4.2, 5.1–5.3
 └──────┬───────┘
        ▼
 ┌──────────────┐
 │   Ответы     │  4 шаблона → answer + sources
 └──────────────┘
```

Каждый шаг — отдельный модуль в `backend/app`. Можно тестировать изолированно.

---

## API

| Метод | Путь | Что делает |
|---|---|---|
| `GET` | `/health` | Проверка живости сервиса |
| `POST` | `/process` | Файл + вопросы → поля + валидация + ответы |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/` | Веб-интерфейс |

Пример запроса:

```bash
curl -X POST http://127.0.0.1:8000/process \
  -F "file=@data/open-001.png" \
  -F 'document_type=study_certificate' \
  -F 'questions=[{"question_id":"q1","question":"Содержит ли документ все обязательные сведения по Положению?"}]'
```

Пример ответа — см. `backend/results`.

---

## Батч-прогон

Открытый сет:

```bash
python scripts/run_open.py
python scripts/evaluate.py \
  --reference data/reference_results.json \
  --predictions results/results_open.json
```

Закрытый сет:

```bash
python scripts/run_closed.py \
  --manifest  data/manifest_closed.json \
  --questions data/questions_closed.json \
  --out       results/results_closed.json
```

Скрипт `evaluate.py` — от организаторов, печатает три метрики
и массив `errors`, если что-то не совпало.

---

## Структура проекта

```
app/
  main.py            FastAPI-приложение
  config.py          пути, лимиты, настройки OCR
  schemas.py         Pydantic-модели
  api/               HTTP-роутеры
  core/
    pdf_io.py        PDF → текст и картинки
    ocr_io.py        PNG/JPG → текст (Tesseract)
    marks.py         детекция подписи и печати
    text_post.py     постобработка OCR
    classifier.py    автоопределение типа
    extract.py       извлечение полей и дат
    rules.py         валидация по Положению
    answers.py       4 шаблона ответов
    service.py       process_full() — точка входа
    pipeline.py      process_document() — батч
  static/            UI (HTML + CSS + JS)
scripts/
  run_open.py        прогон открытого сета
  run_closed.py      прогон закрытого сета
  evaluate.py        оценка (от организаторов)
tests/
  test_pipeline.py   юнит-тесты extract / rules / answers
data/                документы + questions.json + reference
results/             выходные results.json
docs/                скриншоты
```

---

## Тесты

```bash
pytest -q
```

Покрыто: нормализация дат (3 формата), извлечение полей,
валидация (полный / пропущено поле / пропущен флаг),
4 типа ответов. 16 тестов, идут за < 1 сек, не требуют OCR.

---

## Ограничения

- **Внешние API не используются.** Задание запрещает — весь пайплайн
  крутится локально на CPU.
- **Подлинность подписи и печати не проверяется**, только наличие.
  Это сознательное решение: проверка подписи — отдельная задача,
  в реальном деканате её делает человек.
- **Финальное решение принимает сотрудник деканата** (п. 1.3
  Положения). Сервис готовит сводку — не выносит вердикт.
- **OCR ошибается** на плохих сканах. Пайплайн устойчив к типичным
  ошибкам (`З` ↔ `3`, `О` ↔ `0`), но не ко всем.

---

## Команда

| Роль | Задачи |
|---|---|
|Прогер A | OCR, PDF, детекция подписи и печати, FastAPI, схемы |
|Прогер B | классификатор, извлечение полей, правила, ответы, батч, тесты |
| Дизайнер | UI, скриншоты, слайды, оформление |

---

## Лицензия

Учебный проект. Положение о документообороте — внутренний документ
университета, в репозитории не публикуется.