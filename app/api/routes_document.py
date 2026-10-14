import uuid
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.config import settings
from app.core.service import process_full
from app.schemas import AnalyzeResponse, DocType
router = APIRouter(prefix="/api/document", tags=["document"])
@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    question: str = Form(""),
    doc_type: DocType | None = Form(None),
    marks_mode: str = Form("strict"),
    use_llm: str = Form("0"),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_ext:
        raise HTTPException(400, f"Недопустимый формат: {ext}")
    if marks_mode not in ("strict", "loose"):
        marks_mode = "strict"
    use_llm_flag = use_llm in ("1", "true", "True", "yes")
    doc_id = f"upload-{uuid.uuid4().hex[:8]}"
    dest = settings.upload_dir / f"{doc_id}{ext}"
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Файл слишком большой")
    dest.write_bytes(content)
    auto = doc_type is None
    try:
        r = process_full(dest, question, doc_type=doc_type,
                         marks_mode=marks_mode, use_llm=use_llm_flag)
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
@router.post("/highlight")
async def highlight(
    file: UploadFile = File(...),
    doc_type: DocType = Form(...),
    mode: str = Form("all"),
):
    from app.core.highlight import highlight_fields
    from app.core.config_loader import get_type
    print(f"[api] /highlight: doc_type={doc_type}, mode={mode}")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_ext:
        raise HTTPException(400, f"Недопустимый формат: {ext}")

    if mode not in ("all", "problems"):
        mode = "all"
    doc_id = f"highlight-{uuid.uuid4().hex[:8]}"
    dest = settings.upload_dir / f"{doc_id}{ext}"
    dest.write_bytes(await file.read())
    try:
        r = process_full(dest, "", doc_type=doc_type)
    except Exception as e:
        raise HTTPException(500, f"Ошибка обработки: {e}")
    try:
        cfg = get_type(doc_type)
        labels = cfg["labels"]
    except Exception:
        labels = {}
    missing = r["validation"]["missing_fields"]
    print(f"[api] validation status: {r['validation']['status']}")
    print(f"[api] missing_fields: {missing}")
    out = settings.upload_dir / f"{doc_id}_highlighted.png"
    result = highlight_fields(
        dest, r["fields"], labels, out,
        mode=mode, missing_fields=missing,
    )
    if not result:
        raise HTTPException(404, "Нечего подсвечивать")
    return FileResponse(str(result), media_type="image/png")