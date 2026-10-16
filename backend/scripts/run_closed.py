import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.app.core.pipeline import process_document
def resolve_path(item: dict, root: Path) -> Path:
    for key in ("pdf", "pdf_path", "image", "image_path"):
        value = item.get(key)
        if value:
            p = Path(value)
            if not p.is_absolute():
                p = root / p
            return p
    raise ValueError(
        f"У документа {item.get('document_id')} нет ни pdf, ни image"
    )
def main():
    ap = argparse.ArgumentParser(description="Прогон закрытого сета")
    ap.add_argument("--manifest", required=True,
                    help="JSON с документами: [{document_id, document_type, pdf|image}]")
    ap.add_argument("--questions", required=True,
                    help="JSON с вопросами: [{question_id, document_id, question}]")
    ap.add_argument("--out",
                    default=str(ROOT / "results" / "results_closed.json"),
                    help="Куда сохранить results.json")
    ap.add_argument("--skip-errors", action="store_true",
                    help="Не падать на ошибке отдельного документа, писать заглушку")
    args = ap.parse_args()
    manifest_path = Path(args.manifest)
    questions_path = Path(args.questions)
    if not manifest_path.exists():
        print(f"[error] Манифест не найден: {manifest_path}", file=sys.stderr)
        return 1
    if not questions_path.exists():
        print(f"[error] Файл вопросов не найден: {questions_path}", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    q_by_doc: dict[str, list] = {}
    for q in questions:
        q_by_doc.setdefault(q["document_id"], []).append(q)
    print(f"Документов в манифесте: {len(manifest)}")
    print(f"Вопросов всего: {len(questions)}")
    print("-" * 50)
    results = []
    ok = 0
    failed = 0
    for item in manifest:
        did = item.get("document_id")
        dtype = item.get("document_type")
        if not did:
            print(f"[skip] элемент без document_id", file=sys.stderr)
            failed += 1
            continue
        if not dtype:
            print(f"[skip] {did}: не указан document_type", file=sys.stderr)
            failed += 1
            continue
        try:
            path = resolve_path(item, ROOT)
        except ValueError as e:
            print(f"[skip] {did}: {e}", file=sys.stderr)
            failed += 1
            continue
        if not path.exists():
            print(f"[skip] {did}: файл не найден — {path}", file=sys.stderr)
            failed += 1
            continue
        try:
            r = process_document(did, dtype, path, q_by_doc.get(did, []))
            results.append(r)
            print(f"[ok]   {did:<14} {dtype:<26} → {r['validation']['status']}")
            ok += 1
        except Exception as exc:
            print(f"[fail] {did}: {exc}", file=sys.stderr)
            failed += 1
            if not args.skip_errors:
                raise
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"version": "1.0", "documents": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("-" * 50)
    print(f"Успешно:  {ok}")
    print(f"Провалов: {failed}")
    print(f"Результат: {out_path}")
    return 0 if failed == 0 else 2
if __name__ == "__main__":
    sys.exit(main())