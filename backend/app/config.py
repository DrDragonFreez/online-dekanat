from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_prefix="DEKANAT_",
        extra="ignore",
        case_sensitive=False,
    )
    base_dir: Path = Path(__file__).resolve().parent.parent   # = backend/
    data_dir: Path = base_dir / "data"
    upload_dir: Path = base_dir / "data" / "uploads"
    results_dir: Path = base_dir / "results"
    max_upload_mb: int = 20
    tesseract_lang: str = "rus"
    ocr_psm: int = 6
    tesseract_path: str | None = None
    tessdata_prefix: str | None = None
    @property
    def allowed_ext(self) -> set[str]:
        return {".pdf", ".png", ".jpg", ".jpeg"}
settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.results_dir.mkdir(parents=True, exist_ok=True)