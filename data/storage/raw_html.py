from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"


def save_raw_html(source: str, kind: str, source_id: str, html: str) -> str:
    path = RAW_DIR / source / kind / f"{source_id}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return str(path)
