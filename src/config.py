from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("SHOWCASE_DATA_DIR", ROOT_DIR / "data"))
LOG_DIR = Path(os.getenv("SHOWCASE_LOG_DIR", ROOT_DIR / "logs"))
DB_PATH = Path(os.getenv("SHOWCASE_DB_PATH", DATA_DIR / "showcase.db"))
VOICE_OUTPUT_DIR = Path(os.getenv("SHOWCASE_VOICE_OUTPUT_DIR", DATA_DIR / "voice_output"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
VOICE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("SHOWCASE_APP_NAME", "Public Showcase AI Assistant")
    env: str = os.getenv("SHOWCASE_ENV", "dev")
    host: str = os.getenv("SHOWCASE_HOST", "127.0.0.1")
    port: int = int(os.getenv("SHOWCASE_PORT", "8001"))
    debug: bool = _env_bool("SHOWCASE_DEBUG", False)
    log_level: str = os.getenv("SHOWCASE_LOG_LEVEL", "INFO")
    llm_provider: str = os.getenv("SHOWCASE_LLM_PROVIDER", "mock")
    llm_model: str = os.getenv("SHOWCASE_LLM_MODEL", "mock-mini")
    enable_voice_mock: bool = _env_bool("SHOWCASE_ENABLE_VOICE_MOCK", True)
    voice_stt_provider: str = os.getenv("SHOWCASE_VOICE_STT_PROVIDER", "mock")
    voice_tts_provider: str = os.getenv("SHOWCASE_VOICE_TTS_PROVIDER", "mock")
    api_token: str = os.getenv("SHOWCASE_API_TOKEN", "").strip()
    frontend_enabled: bool = _env_bool("SHOWCASE_FRONTEND_ENABLED", True)
    db_path: Path = DB_PATH
    voice_output_dir: Path = VOICE_OUTPUT_DIR


settings = Settings()

