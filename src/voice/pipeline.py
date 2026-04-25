from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.voice.adapters import CoquiTTSAdapter, EdgeTTSAdapter, WhisperSTTAdapter

from src.config import settings
from src.utils.logging import logger


@dataclass
class VoiceResult:
    mode: str
    text: str
    message: str
    audio_path: str = ""
    available: bool = True


class VoicePipeline:
    def __init__(self, enable_mock: bool = True):
        self.enable_mock = enable_mock
        self.whisper = WhisperSTTAdapter()
        self.edge_tts = EdgeTTSAdapter()
        self.coqui_tts = CoquiTTSAdapter()

    def transcribe(self, sample_text: str) -> VoiceResult:
        cleaned = sample_text.strip()
        if not cleaned:
            return VoiceResult("mock-stt", "", "No speech detected.")
        logger.info("Mock STT received text: %s", cleaned)
        return VoiceResult("mock-stt", cleaned, "Transcription completed in mock mode.")

    def transcribe_audio_file(self, audio_path: str, provider: str | None = None) -> VoiceResult:
        selected = (provider or settings.voice_stt_provider or "mock").lower()
        if selected == "whisper":
            result = self.whisper.transcribe_file(audio_path)
            return VoiceResult(
                mode="whisper-stt",
                text=result.text,
                message=result.message,
                available=result.available,
            )

        if selected != "mock":
            return VoiceResult(mode=selected, text="", message=f"Unsupported STT provider: {selected}", available=False)

        return VoiceResult("mock-stt", "", "Mock STT expects direct text input.")

    def speak(self, text: str) -> VoiceResult:
        cleaned = text.strip()
        logger.info("Mock TTS output: %s", cleaned)
        return VoiceResult("mock-tts", cleaned, "Speech queued in mock mode.")

    async def speak_with_provider(self, text: str, provider: str | None = None) -> VoiceResult:
        cleaned = text.strip()
        selected = (provider or settings.voice_tts_provider or "mock").lower()

        if selected == "edge":
            result = await self.edge_tts.synthesize(cleaned)
            return VoiceResult(
                mode="edge-tts",
                text=result.text,
                message=result.message,
                audio_path=result.audio_path,
                available=result.available,
            )

        if selected == "coqui":
            result = self.coqui_tts.synthesize(cleaned)
            return VoiceResult(
                mode="coqui-tts",
                text=result.text,
                message=result.message,
                audio_path=result.audio_path,
                available=result.available,
            )

        if selected != "mock":
            return VoiceResult(mode=selected, text=cleaned, message=f"Unsupported TTS provider: {selected}", available=False)

        logger.info("Mock TTS output: %s", cleaned)
        return VoiceResult("mock-tts", cleaned, "Speech queued in mock mode.")

    def capabilities(self) -> dict[str, Any]:
        return {
            "stt": {
                "default_provider": settings.voice_stt_provider,
                "providers": ["mock", "whisper"],
            },
            "tts": {
                "default_provider": settings.voice_tts_provider,
                "providers": ["mock", "edge", "coqui"],
            },
            "voice_output_dir": str(settings.voice_output_dir),
        }


voice_pipeline = VoicePipeline(enable_mock=settings.enable_voice_mock)
