"""Video provider abstraction + background generation orchestration.

The provider is selected from Settings. If no provider is configured OR the
chosen model is not video-capable, the generation fails HONESTLY (no fake
output) — a message tells the user to configure one or copy the prompt into
Google Flow / an external tool.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.database import SessionLocal
from app.models.video import Generation
from app.services.config_service import get_config
from app.services.nvidia_service import NvidiaService, NvidiaError

logger = logging.getLogger(__name__)


class VideoProvider:
    name = "base"

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def get_status(self, generation_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def supports_video(self) -> bool:
        return False


class NvidiaVideoProvider(VideoProvider):
    name = "nvidia"

    def __init__(self, api_key: str, model: str, base_url: str):
        self.service = NvidiaService(api_key, model, base_url)

    def supports_video(self) -> bool:
        return self.service.supports_video()

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        return self.service.generate_video(
            prompt,
            aspect_ratio=kwargs.get("aspect_ratio", "9:16"),
            duration_seconds=kwargs.get("duration_seconds", 5),
            resolution=kwargs.get("resolution", "720p"),
            negative_prompt=kwargs.get("negative_prompt", ""),
        )

    def get_status(self, generation_id: str) -> Dict[str, Any]:
        return self.service.get_status(generation_id)


def get_provider(db: Session) -> Optional[VideoProvider]:
    name = (get_config(db, "VIDEO_PROVIDER", "") or "").lower()
    if not name:
        return None
    if name == "nvidia":
        key = get_config(db, "NVIDIA_API_KEY", "")
        model = get_config(db, "NVIDIA_MODEL", "")
        base_url = get_config(db, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        if not key or not model:
            return None
        return NvidiaVideoProvider(key, model, base_url)
    # Other providers can be added here. If none matches we return None
    # and the orchestration layer surfaces a clear error.
    return None


# ─── Background orchestration ──────────────────────────────

def _update(db: Session, gen: Generation, **fields) -> None:
    for k, v in fields.items():
        setattr(gen, k, v)
    gen.updated_at = datetime.utcnow()
    db.commit()


def _run(gen_id: int) -> None:
    db = SessionLocal()
    try:
        gen = db.get(Generation, gen_id)
        if not gen:
            logger.error("Generation %s not found", gen_id)
            return

        logger.info("Running generation %s (provider=%s model=%s)",
                    gen_id, gen.video_provider, gen.video_model)

        _update(db, gen, status="preparing", progress=5)

        provider = get_provider(db)
        if provider is None:
            _update(db, gen, status="failed",
                    error_message=("Belum ada video provider yang terkonfigurasi. "
                                   "Isi API key + model di Settings → Video Generation, "
                                   "atau copy prompt dan pakai jalur gratis seperti Google Flow."))
            return

        if not provider.supports_video():
            _update(db, gen, status="failed",
                    error_message=(f"Model {gen.video_model!r} di provider "
                                   f"{provider.name} tidak mendukung video generation. "
                                   "Pilih model video-capable (misal nvidia/cosmos-vid-1) di Settings."))
            return

        _update(db, gen, status="submitting", progress=15)
        try:
            result = provider.generate(
                gen.prompt, aspect_ratio=gen.aspect_ratio,
                duration_seconds=5, resolution="720p",
                negative_prompt=gen.negative_prompt,
            )
        except NvidiaError as exc:
            _update(db, gen, status="failed", error_message=str(exc))
            return
        except Exception as exc:
            logger.exception("Unexpected generation error.")
            _update(db, gen, status="failed", error_message=f"Generation error: {exc}")
            return

        provider_gen_id = result.get("generation_id", "")
        _update(db, gen, status="generating", progress=40, generation_id=provider_gen_id)

        deadline = time.time() + 600
        while time.time() < deadline:
            time.sleep(5)
            try:
                st = provider.get_status(provider_gen_id)
            except Exception as exc:
                logger.warning("Status poll failed: %s", exc)
                continue

            status = (st.get("status") or "").lower()
            if status in ("succeeded", "completed", "success"):
                url = st.get("video_url") or st.get("output_url") or st.get("url", "")
                _update(db, gen, status="completed", progress=100,
                        completed_at=datetime.utcnow(), video_path=url)
                return
            if status in ("failed", "error"):
                _update(db, gen, status="failed",
                        error_message=st.get("error", "Provider reported failure."))
                return
            if "progress" in st:
                try:
                    _update(db, gen, progress=int(st["progress"]))
                except Exception:
                    pass

        _update(db, gen, status="failed", error_message="Timed out after 10 minutes.")
    finally:
        db.close()


def enqueue_generation(gen_id: int) -> None:
    t = threading.Thread(target=_run, args=(gen_id,), daemon=True)
    t.start()
