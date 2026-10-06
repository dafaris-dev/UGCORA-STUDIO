"""Runtime configuration helpers: reads from env, with DB overrides."""
import os
from typing import Optional
from sqlalchemy.orm import Session
from app.models.setting import Setting


SETTING_KEYS = {
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "NVIDIA_API_KEY",
    "NVIDIA_MODEL",
    "NVIDIA_BASE_URL",
    "VIDEO_PROVIDER",
    "VOICE_PROVIDER",
}


def get_config(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).one_or_none()
    if row and row.value:
        return row.value
    return os.getenv(key, default)


def set_config(db: Session, key: str, value: str) -> None:
    row = db.query(Setting).filter(Setting.key == key).one_or_none()
    if row is None:
        row = Setting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()


def mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * len(value)
    return "••••••••••" + value[-4:]
