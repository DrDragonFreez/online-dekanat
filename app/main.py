from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import (
    routes_ask,
    routes_batch,
    routes_document,
    routes_health,
    routes_static,
)
from app.config import settings
app = FastAPI(
    title="Деканыч API",
    version="1.0.0",
    description="Цифровой секретарь деканата: OCR → поля → проверка → ответ",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/static",
    StaticFiles(directory=str(settings.base_dir / "app" / "static")),
    name="static",
)
app.include_router(routes_health.router)
app.include_router(routes_document.router)
app.include_router(routes_ask.router)
app.include_router(routes_batch.router)
app.include_router(routes_static.router)