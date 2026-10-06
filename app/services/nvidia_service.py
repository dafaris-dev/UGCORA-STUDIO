"""NVIDIA integration (modular).

Uses NVIDIA NIM / integrate.api.nvidia.com style endpoints via httpx.
Not every model supports video generation; the service exposes a capability
check and clearly reports when a configured model cannot produce video.
"""
import logging
from typing import Dict, Any, Optional, List

import httpx

logger = logging.getLogger(__name__)


class NvidiaError(Exception):
    pass


class NvidiaService:
    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = (api_key or "").strip()
        self.model = (model or "").strip()
        self.base_url = (base_url or "https://integrate.api.nvidia.com/v1").rstrip("/")

    # ---- Helpers ----
    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise NvidiaError("NVIDIA API key is not configured.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> httpx.Response:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=30.0) as c:
            return c.get(url, headers=self._headers())

    def _post(self, path: str, body: Dict[str, Any], timeout: float = 120.0) -> httpx.Response:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=timeout) as c:
            return c.post(url, headers=self._headers(), json=body)

    # ---- Public API ----
    def list_models(self) -> List[str]:
        try:
            resp = self._get("/models")
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
        except Exception as exc:
            logger.warning("NVIDIA list_models failed: %s", exc)
        return []

    def test_connection(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"ok": False, "error": "NVIDIA API key is not configured."}
        try:
            resp = self._get("/models")
            if resp.status_code == 200:
                data = resp.json()
                ids = [m.get("id") for m in data.get("data", [])]
                has_model = self.model in ids if self.model else False
                return {
                    "ok": True,
                    "base_url": self.base_url,
                    "model": self.model,
                    "models_available": len(ids),
                    "configured_model_available": has_model,
                }
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": f"Network error: {exc}"}

    def generate_inference(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Chat/completions style inference for text-capable NVIDIA NIM models."""
        if not self.model:
            raise NvidiaError("NVIDIA model is not configured.")
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 512),
        }
        resp = self._post("/chat/completions", body)
        if resp.status_code != 200:
            raise NvidiaError(f"NVIDIA inference failed ({resp.status_code}): {resp.text[:400]}")
        data = resp.json()
        try:
            return {"text": data["choices"][0]["message"]["content"], "raw": data}
        except Exception as exc:
            raise NvidiaError(f"Unexpected NVIDIA response: {exc}") from exc

    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        if not self.model:
            raise NvidiaError("NVIDIA model is not configured.")
        body = {"prompt": prompt, **kwargs}
        resp = self._post(f"/genai/{self.model}", body)
        if resp.status_code != 200:
            raise NvidiaError(f"Image generation failed ({resp.status_code}): {resp.text[:400]}")
        return resp.json()

    def supports_video(self) -> bool:
        """Heuristic: NVIDIA model id hints at video capability."""
        if not self.model:
            return False
        m = self.model.lower()
        return any(tag in m for tag in ("cosmos", "video", "sora", "svd", "stable-video"))

    def generate_video(self, prompt: str, aspect_ratio: str = "9:16",
                       duration_seconds: int = 5, resolution: str = "720p",
                       negative_prompt: str = "") -> Dict[str, Any]:
        """Attempt video generation.

        Returns a dict:
          { "ok": True, "generation_id": str, "status": str }
        or raises NvidiaError if the configured model doesn't support video.
        """
        if not self.supports_video():
            raise NvidiaError(
                "This configured NVIDIA model does not support video generation."
            )
        body = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration_seconds,
            "resolution": resolution,
            "negative_prompt": negative_prompt,
        }
        resp = self._post(f"/genai/{self.model}", body, timeout=180.0)
        if resp.status_code not in (200, 201, 202):
            raise NvidiaError(f"Video generation failed ({resp.status_code}): {resp.text[:400]}")
        data = resp.json()
        gen_id = data.get("id") or data.get("generation_id") or data.get("request_id") or ""
        return {"ok": True, "generation_id": gen_id, "status": data.get("status", "submitted"), "raw": data}

    def get_status(self, generation_id: str) -> Dict[str, Any]:
        if not generation_id:
            raise NvidiaError("Missing generation id.")
        resp = self._get(f"/genai/status/{generation_id}")
        if resp.status_code != 200:
            raise NvidiaError(f"Status check failed ({resp.status_code}): {resp.text[:400]}")
        return resp.json()
