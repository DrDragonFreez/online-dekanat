from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DEKANAT_")
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    upload_dir: Path = base_dir / "uploads"
    result_dir: Path = base_dir / "results"
    max_upload_mb: int=20
    tesseract_lang: str="rus"
    ocr_psm: int=6
    @property
    def allowed_ext(selfSelf)->set[str]:
        return{".pdf",".png",".jpg",".jpeg"}
settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.result_dir.mkdir(parents=True, exist_ok=True)