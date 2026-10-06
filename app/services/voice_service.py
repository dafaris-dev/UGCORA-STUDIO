"""Modular voice provider abstraction - no providers configured by default."""
from typing import List, Dict, Any


VOICE_STYLES = ["Casual", "Friendly", "Professional", "Energetic", "Calm", "Luxury"]
VOICE_GENDERS = ["Female", "Male"]
LANGUAGES = ["English", "Spanish", "French", "German", "Portuguese", "Italian", "Dutch", "Arabic", "Japanese", "Korean"]


class VoiceProvider:
    name = "base"

    def list_voices(self) -> List[Dict[str, Any]]:
        return []

    def test_connection(self) -> Dict[str, Any]:
        return {"ok": False, "error": "No voice provider configured."}

    def synthesize(self, text: str, voice_id: str, **kwargs) -> bytes:
        raise NotImplementedError("No voice provider configured.")


class NoneVoiceProvider(VoiceProvider):
    name = "none"

    def test_connection(self) -> Dict[str, Any]:
        return {"ok": True, "provider": "none", "note": "No voice provider configured; TTS not performed."}


def get_voice_provider(name: str) -> VoiceProvider:
    name = (name or "none").lower()
    if name == "none":
        return NoneVoiceProvider()
    return NoneVoiceProvider()
