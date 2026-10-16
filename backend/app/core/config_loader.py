from functools import lru_cache
from pathlib import Path
import yaml
CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "doc_types.yaml"
)
@lru_cache(maxsize=1)
def load_doc_types() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Конфиг не найден: {CONFIG_PATH}")
    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("doc_types.yaml должен содержать словарь типов")
    return data
def get_type(doc_type: str) -> dict:
    data = load_doc_types()
    if doc_type not in data:
        raise ValueError(f"Неизвестный тип документа: {doc_type}")
    return data[doc_type]
def all_types() -> list[str]:
    return list(load_doc_types().keys())
def all_titles() -> dict[str, str]:
    return {k: v.get("title", k) for k, v in load_doc_types().items()}