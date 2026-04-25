from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import settings


@dataclass
class AdapterResult:
    available: bool
    message: str
    text: str = ""
    audio_path: str = ""


class WhisperSTTAdapter:
    provider_name = "whisper"

    def transcribe_file(self, audio_path: str) -> AdapterResult:
        try:
            import whisper
        except ImportError:
            return AdapterResult(False, "Whisper STT dependency not installed.")

        path = Path(audio_path)
        if not path.exists():
            return AdapterResult(False, f"Audio file not found: {audio_path}")

        model = whisper.load_model("base")
        result = model.transcribe(str(path))
        return AdapterResult(True, "Whisper transcription completed.", text=(result.get("text") or "").strip())


class EdgeTTSAdapter:
    provider_name = "edge-tts"

    async def synthesize(self, text: str, voice: str = "en-US-JennyNeural") -> AdapterResult:
        try:
            import edge_tts
        except ImportError:
            return AdapterResult(False, "edge-tts dependency not installed.")

        file_name = f"edge_tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        output_path = settings.voice_output_dir / file_name
        communicator = edge_tts.Communicate(text, voice)
        await communicator.save(str(output_path))
        return AdapterResult(True, "Edge TTS synthesis completed.", text=text, audio_path=str(output_path))


class CoquiTTSAdapter:
    provider_name = "coqui"

    def synthesize(self, text: str, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC") -> AdapterResult:
        try:
            from TTS.api import TTS
        except ImportError:
            return AdapterResult(False, "coqui-tts dependency not installed.")

        file_name = f"coqui_tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        output_path = settings.voice_output_dir / file_name
        tts = TTS(model_name=model_name)
        tts.tts_to_file(text=text, file_path=str(output_path))
        return AdapterResult(True, "Coqui TTS synthesis completed.", text=text, audio_path=str(output_path))
