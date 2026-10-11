import uuid
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.config import settings
from app.core.service import process_full
from app.schemas import AnalyzeResponse, DocType
router = APIRouter(prefix="/api/document", tags=["document"])
@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    question: str = Form(""),
    doc_type: DocType | None = Form(None),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_ext:
        raise HTTPException(400, f"Недопустимый формат: {ext}")
    doc_id = f"upload-{uuid.uuid4().hex[:8]}"
    dest = settings.upload_dir / f"{doc_id}{ext}"
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Файл слишком большой")
    dest.write_bytes(content)
    auto = doc_type is None
    try:
        r = process_full(dest, question, doc_type=doc_type)
    except NotImplementedError:
        raise HTTPException(
            503,
        )
    except Exception as e:
        raise HTTPException(500, f"Ошибка обработки: {e}")
    return AnalyzeResponse(
        document_id=doc_id,
        doc_type=r["doc_type"],
        doc_type_auto=auto,
        kind=r["kind"],
        text=r["text"],
        fields=r["fields"],
        validation=r["validation"],
        answer=r["answer"],
    )