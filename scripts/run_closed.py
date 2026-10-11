import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.pipeline import process_document


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True,
                    help="JSON: [{document_id, document_type, image|pdf}]")
    ap.add_argument("--questions", required=True,
                    help="JSON: [{question_id, document_id, question}]")
    ap.add_argument("--out",
                    default=str(ROOT / "results" / "results_closed.json"))
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    qs = json.loads(Path(args.questions).read_text(encoding="utf-8"))

    q_by_doc: dict[str, list] = {}
    for q in qs:
        q_by_doc.setdefault(q["document_id"], []).append(q)

    results = []
    for item in manifest:
        did = item["document_id"]
        dtype = item.get("document_type") or "study_certificate"
        path = item.get("pdf") or item.get("image")
        r = process_document(did, dtype, path, q_by_doc.get(did, []))
        results.append(r)
        print(f"[ok] {did} → {r['validation']['status']}")

    out_p = Path(args.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(
        json.dumps({"version": "1.0", "documents": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Wrote {out_p}")

if __name__ == "__main__":
    main()
