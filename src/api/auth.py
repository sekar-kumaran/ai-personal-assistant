from __future__ import annotations

from fastapi import Header, HTTPException

from src.config import settings


def validate_api_token(x_api_token: str | None = Header(default=None)) -> None:
    if not settings.api_token:
        return
    if x_api_token != settings.api_token:
        raise HTTPException(status_code=401, detail="Invalid API token")
