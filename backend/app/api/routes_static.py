from fastapi import APIRouter
from fastapi.responses import FileResponse
from app.config import settings
router = APIRouter(tags=["ui"])
STATIC = settings.base_dir.parent / "frontend"
@router.get("/")
def index():
    return FileResponse(STATIC / "index.html")
@router.get("/uploads/{name}")
def uploaded(name: str):
    p = settings.upload_dir / name
    if not p.exists():
        return {"error": "not found"}
    return FileResponse(p)