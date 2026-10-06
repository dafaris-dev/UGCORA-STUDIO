"""Local file storage helpers - modular to allow swapping to S3 later."""
import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

logger = logging.getLogger(__name__)

DATA_ROOT = Path("data")

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}


def _ensure_dir(subdir: str) -> Path:
    path = DATA_ROOT / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(upload: UploadFile, subdir: str, allowed: Optional[set] = None) -> str:
    """Save an UploadFile to data/<subdir>/ and return a relative path."""
    if not upload or not upload.filename:
        return ""
    ext = Path(upload.filename).suffix.lower()
    if allowed is not None and ext not in allowed:
        raise ValueError(f"Unsupported file type: {ext}")
    folder = _ensure_dir(subdir)
    unique = f"{uuid.uuid4().hex}{ext}"
    dest = folder / unique
    with dest.open("wb") as f:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    rel = str(dest.as_posix())
    logger.info("Saved upload %s -> %s", upload.filename, rel)
    return rel


def save_bytes(data: bytes, subdir: str, suffix: str = ".bin") -> str:
    folder = _ensure_dir(subdir)
    name = f"{uuid.uuid4().hex}{suffix}"
    dest = folder / name
    dest.write_bytes(data)
    return str(dest.as_posix())


def delete_file(rel_path: str) -> None:
    if not rel_path:
        return
    try:
        p = Path(rel_path)
        if p.exists() and p.is_file():
            p.unlink()
    except Exception as exc:
        logger.warning("Failed to delete %s: %s", rel_path, exc)


def read_bytes(rel_path: str) -> Optional[bytes]:
    if not rel_path:
        return None
    p = Path(rel_path)
    if not p.exists():
        return None
    return p.read_bytes()
