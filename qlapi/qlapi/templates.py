"""Flat-file JSON storage for label-editor templates."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(
    os.getenv("QL_TEMPLATES_DIR", Path(__file__).parent / "data" / "templates")
)
"""Directory where templates are stored. Set QL_TEMPLATES_DIR to point it at,
e.g., a Docker volume so templates survive container recreation."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(template_id: str) -> Path:
    return DATA_DIR / f"{template_id}.json"


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def list_templates() -> list:
    """Return metadata (no canvas) for every stored template."""
    _ensure_dir()
    meta = []
    for path in DATA_DIR.glob("*.json"):
        data = get_template(path.stem)
        data.pop("canvas", None)
        meta.append(data)
    return meta


def get_template(template_id: str) -> dict:
    """Return the full stored template or raise FileNotFoundError."""
    with _path(template_id).open() as f:
        return json.load(f)


def save_template(template_id: str, data: dict) -> dict:
    """Persist a template under id and return the stored payload."""
    _ensure_dir()
    payload = dict(data)
    payload["id"] = template_id
    _path(template_id).write_text(json.dumps(payload, indent=2))
    return payload


def delete_template(template_id: str) -> bool:
    """Remove a template. Returns False if it did not exist."""
    path = _path(template_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def new_id() -> str:
    return uuid.uuid4().hex
