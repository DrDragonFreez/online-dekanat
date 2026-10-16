import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from app.core.service import read_text
path = ROOT / "data" / "documents" / "open-005.png"
text, kind = read_text(path)
print("=== KIND ===")
print(kind)
print()
print("=== СЫРОЙ ТЕКСТ ===")
for i, line in enumerate(text.splitlines()):
    print(f"{i:>3}: {line!r}")