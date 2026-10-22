"""Secure environment configuration for PANOPTICON."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()

HACKATHON_QLOO_URL = (
    "https://hackathon.api.qloo.com/v2/insights"
)

PRODUCTION_QLOO_URL = (
    "https://api.qloo.com/v2/insights"
)


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    qloo_api_key: str | None
    qloo_api_url: str
    groq_api_key: str | None
    groq_model: str
    groq_api_url: str
    request_timeout: float


def _configured_qloo_url() -> str:
    """Validate and select the appropriate Qloo API endpoint."""

    environment = os.getenv(
        "QLOO_API_ENVIRONMENT", "hackathon"
    ).strip().lower()

    configured_url = os.getenv(
        "QLOO_API_URL", ""
    ).strip()

    if environment not in {"hackathon", "production"}:
        raise ValueError(
            "QLOO_API_ENVIRONMENT must be "
            "'hackathon' or 'production'."
        )

    default_url = (
        HACKATHON_QLOO_URL
        if environment == "hackathon"
        else PRODUCTION_QLOO_URL
    )

    url = configured_url or default_url
    parts = urlsplit(url)

    if parts.scheme != "https" or not parts.netloc:
        raise ValueError(
            "QLOO_API_URL must be a valid HTTPS URL."
        )

    expected_host = (
        "hackathon.api.qloo.com"
        if environment == "hackathon"
        else "api.qloo.com"
    )

    if parts.hostname not in {
        "api.qloo.com",
        "hackathon.api.qloo.com",
    }:
        raise ValueError(
            "QLOO_API_URL must use an official Qloo API host."
        )

    path = parts.path or "/v2/insights"

    return urlunsplit(
        (
            "https",
            expected_host,
            path,
            parts.query,
            "",
        )
    )


def get_settings() -> Settings:
    """Load and validate application settings."""

    raw_timeout = os.getenv(
        "PANOPTICON_REQUEST_TIMEOUT", "20"
    )

    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise ValueError(
            "PANOPTICON_REQUEST_TIMEOUT must be a number."
        ) from exc

    if not 0 < timeout <= 120:
        raise ValueError(
            "PANOPTICON_REQUEST_TIMEOUT must be "
            "greater than 0 and at most 120."
        )

    return Settings(
        qloo_api_key=(
            os.getenv("QLOO_API_KEY", "").strip() or None
        ),
        qloo_api_url=_configured_qloo_url(),
        groq_api_key=(
            os.getenv("GROQ_API_KEY", "").strip() or None
        ),
        groq_model=os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b",
        ).strip(),
        groq_api_url=os.getenv(
            "GROQ_API_URL",
            "https://api.groq.com/openai/v1/chat/completions",
        ).strip(),
        request_timeout=timeout,
    )