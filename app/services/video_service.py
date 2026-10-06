"""Video provider abstraction + background generation orchestration.

Frontend hits POST /api/videos/generate which:
  1) validates the inputs,
  2) builds the final prompt,
  3) picks the provider (NVIDIA by default),
  4) submits the generation and tracks status in DB.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.database import SessionLocal
from app.models.video import VideoGeneration
from app.services.config_service import get_config
from app.services.nvidia_service import NvidiaService, NvidiaError

logger = logging.getLogger(__name__)


class VideoProvider:
    name = "base"

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def get_status(self, generation_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def download_result(self, generation_id: str) -> Optional[bytes]:
        raise NotImplementedError

    def cancel_generation(self, generation_id: str) -> bool:
        return False

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


def get_provider(db: Session) -> VideoProvider:
    name = (get_config(db, "VIDEO_PROVIDER", "nvidia") or "nvidia").lower()
    if name == "nvidia":
        return NvidiaVideoProvider(
            api_key=get_config(db, "NVIDIA_API_KEY", ""),
            model=get_config(db, "NVIDIA_MODEL", ""),
            base_url=get_config(db, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        )
    raise ValueError(f"Unknown video provider: {name}")


# ----- Background orchestration -----

def _update(db: Session, video: VideoGeneration, **fields) -> None:
    for k, v in fields.items():
        setattr(video, k, v)
    video.updated_at = datetime.utcnow()
    db.commit()


def _run_generation(video_id: int) -> None:
    db = SessionLocal()
    try:
        video = db.get(VideoGeneration, video_id)
        if not video:
            logger.error("Video %s not found for generation.", video_id)
            return

        logger.info("Starting generation for video %s (provider=%s model=%s)",
                    video_id, video.provider, video.model)

        _update(db, video, status="preparing", progress=5)
        time.sleep(0.1)

        _update(db, video, status="submitting", progress=15)
        try:
            provider = get_provider(db)
            video.provider = provider.name
            db.commit()
        except Exception as exc:
            _update(db, video, status="failed", error_message=f"Provider init failed: {exc}")
            return

        if not provider.supports_video():
            _update(
                db, video,
                status="failed",
                error_message="This configured provider/model does not support video generation."
            )
            return

        try:
            result = provider.generate(
                video.prompt,
                aspect_ratio=video.aspect_ratio,
                duration_seconds=video.duration_seconds,
                resolution=video.resolution,
                negative_prompt=video.negative_prompt,
            )
        except NvidiaError as exc:
            _update(db, video, status="failed", error_message=str(exc))
            return
        except Exception as exc:
            logger.exception("Unexpected generation error.")
            _update(db, video, status="failed", error_message=f"Generation error: {exc}")
            return

        gen_id = result.get("generation_id", "")
        _update(db, video, status="generating", progress=40, generation_id=gen_id)

        # Poll for status up to ~10 minutes
        deadline = time.time() + 600
        while time.time() < deadline:
            time.sleep(5)
            try:
                st = provider.get_status(gen_id)
            except Exception as exc:
                logger.warning("Status poll failed: %s", exc)
                continue

            status = (st.get("status") or "").lower()
            if status in ("succeeded", "completed", "success"):
                url = st.get("video_url") or st.get("output_url") or st.get("url", "")
                _update(db, video, status="completed", progress=100,
                        completed_at=datetime.utcnow(), video_path=url)
                return
            if status in ("failed", "error"):
                _update(db, video, status="failed",
                        error_message=st.get("error", "Provider reported failure."))
                return
            # progress update
            if "progress" in st:
                try:
                    _update(db, video, progress=int(st["progress"]))
                except Exception:
                    pass

        _update(db, video, status="failed", error_message="Generation timed out after 10 minutes.")
    finally:
        db.close()


def enqueue_generation(video_id: int) -> None:
    t = threading.Thread(target=_run_generation, args=(video_id,), daemon=True)
    t.start()
