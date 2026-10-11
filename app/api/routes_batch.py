import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.core.pipeline import process_document
from app.schemas import BatchRequest, BatchResponse
router = APIRouter(prefix="/api/batch", tags=["batch"])
@router.post("/run", response_model=BatchResponse)
def run_batch(req: BatchRequest):
    manifest_p = Path(req.manifest_path)
    questions_p = Path(req.questions_path)
    if not manifest_p.exists():
        raise HTTPException(404, f"Manifest не найден: {manifest_p}")
    if not questions_p.exists():
        raise HTTPException(404, f"Questions не найден: {questions_p}")
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    qs = json.loads(questions_p.read_text(encoding="utf-8"))
    q_by_doc: dict[str, list] = {}
    for q in qs:
        q_by_doc.setdefault(q["document_id"], []).append(q)
    out = []
    for item in manifest:
        did = item["document_id"]
        dtype = item.get("document_type") or "study_certificate"
        path = item.get("pdf") or item.get("image")
        r = process_document(did, dtype, path, q_by_doc.get(did, []))
        out.append(r)
    out_p = Path(req.out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(
        json.dumps({"version": "1.0", "documents": out},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return BatchResponse(
        documents=len(out),
        questions=sum(len(d["answers"]) for d in out),
        out_path=str(out_p),
    )