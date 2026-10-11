import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.pipeline import process_document


def main():
    data = ROOT / "data"
    docs = json.loads((data / "documents.json").read_text(encoding="utf-8"))
    qs = json.loads((data / "questions.json").read_text(encoding="utf-8"))

    q_by_doc: dict[str, list] = {}
    for q in qs:
        q_by_doc.setdefault(q["document_id"], []).append(q)

    results = []
    for d in docs:
        did = d["document_id"]
        dtype = d["document_type"]
        pdf = data / d["pdf"]
        png = data / d["images"]
        path = pdf if pdf.exists() else png
        r = process_document(did, dtype, path, q_by_doc.get(did, []))
        results.append(r)
        print(f"[ok] {did} → {r['validation']['status']}")

    out = ROOT / "results" / "results_open.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"version": "1.0", "documents": results},
            ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

