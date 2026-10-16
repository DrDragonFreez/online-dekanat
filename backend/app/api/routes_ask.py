from fastapi import APIRouter, HTTPException
from app.config import settings
from app.core.service import process_full
from app.schemas import AskRequest, AskResponse
router = APIRouter(prefix="/api/document", tags=["document"])
@router.post("/{document_id}/ask", response_model=AskResponse)
def ask(document_id: str, req: AskRequest):
    matches = list(settings.upload_dir.glob(f"{document_id}.*"))
    if not matches:
        raise HTTPException(404, "Документ не найден. Сначала загрузите через /analyze.")
    path = matches[0]
    r = process_full(path, req.question, doc_type=req.doc_type)
    return AskResponse(
        doc_type=r["doc_type"],
        fields=r["fields"],
        validation=r["validation"],
        answer=r["answer"],
    )