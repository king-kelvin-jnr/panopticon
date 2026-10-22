
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


def _setting(name: str, default: str = "") -> str:
    """Read a setting from the environment or Streamlit secrets.

    Environment variables take priority, so existing local .env
    configuration continues to work. Streamlit secrets provide the
    fallback for cloud deployments.
    """
    environment_value = os.getenv(name)

    if environment_value and environment_value.strip():
        return environment_value.strip()

    try:
        import streamlit as st

        secret_value = st.secrets.get(name, default)

        if secret_value is None:
            return default

        return str(secret_value).strip()

    except Exception:
        # Streamlit secrets may not be configured in a local environment.
        return default


@dataclass(frozen=True)
class Settings:
    """Application settings."""

    qloo_api_key: str | None
    qloo_api_url: str
    groq_api_key: str | None
    groq_model: str
    groq_api_url: str
    request_timeout: float


def _configured_qloo_url() -> str:
    """Validate and select the appropriate Qloo API endpoint."""

    environment = _setting(
        "QLOO_API_ENVIRONMENT", "hackathon"
    ).lower()

    configured_url = _setting("QLOO_API_URL")

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

    if parts.hostname not in {
        "api.qloo.com",
        "hackathon.api.qloo.com",
    }:
        raise ValueError(
            "QLOO_API_URL must use an official Qloo API host."
        )

    expected_host = (
        "hackathon.api.qloo.com"
        if environment == "hackathon"
        else "api.qloo.com"
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

    raw_timeout = _setting(
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
        qloo_api_key=_setting("QLOO_API_KEY") or None,
        qloo_api_url=_configured_qloo_url(),
        groq_api_key=_setting("GROQ_API_KEY") or None,
        groq_model=_setting(
            "GROQ_MODEL", "openai/gpt-oss-120b"
        ),
        groq_api_url=_setting(
            "GROQ_API_URL",
            "https://api.groq.com/openai/v1/chat/completions",
        ),
        request_timeout=timeout,
    )
