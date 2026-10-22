"""PANOPTICON Qloo API client.

Supports entity search and Qloo Insights using entity UUIDs or URNs.
Only live API responses are reported as live data.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests
from requests.structures import CaseInsensitiveDict

from .config import Settings, get_settings


_ENTITY_URN_PATTERN = re.compile(
    r"^urn:entity:[A-Za-z0-9:_./-]+$"
)

_ENTITY_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)

_SUPPORTED_ENTITY_TYPES = frozenset(
    {
        "urn:entity:artist",
        "urn:entity:book",
        "urn:entity:brand",
        "urn:entity:destination",
        "urn:entity:movie",
        "urn:entity:person",
        "urn:entity:place",
        "urn:entity:podcast",
        "urn:entity:tv_show",
        "urn:entity:videogame",
    }
)


class QlooError(RuntimeError):
    """An API error safe to display without exposing credentials."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.public_message = message


def parse_entity_ids(
    raw: str | list[str] | tuple[str, ...],
) -> list[str]:
    """Validate and deduplicate Qloo entity UUIDs or entity URNs."""

    candidates = (
        re.split(r"[,\n]", raw)
        if isinstance(raw, str)
        else list(raw)
    )

    identifiers: list[str] = []

    for candidate in candidates:
        identifier = str(candidate).strip()

        if not identifier:
            continue

        is_urn = bool(_ENTITY_URN_PATTERN.fullmatch(identifier))
        is_uuid = bool(_ENTITY_UUID_PATTERN.fullmatch(identifier))

        if not (is_urn or is_uuid):
            raise QlooError(
                "Each cultural input must be a valid Qloo entity UUID "
                "or an entity URN beginning with 'urn:entity:'."
            )

        if identifier not in identifiers:
            identifiers.append(identifier)

    if len(identifiers) > 20:
        raise QlooError(
            "Provide no more than 20 distinct Qloo entity identifiers."
        )

    return identifiers


def parse_entity_urns(
    raw: str | list[str] | tuple[str, ...],
) -> list[str]:
    """Backward-compatible parser; now accepts UUIDs and URNs."""

    return parse_entity_ids(raw)


def _search_url(insights_url: str) -> str:
    """Build the search URL using the configured Qloo API host."""

    parts = urlsplit(insights_url)

    if parts.scheme != "https" or not parts.hostname:
        raise QlooError(
            "Qloo API URL must be a valid HTTPS URL."
        )

    if parts.hostname not in {
        "api.qloo.com",
        "hackathon.api.qloo.com",
    }:
        raise QlooError(
            "The configured host is not an approved Qloo API host."
        )

    return urlunsplit(
        (
            "https",
            parts.netloc,
            "/search",
            "",
            "",
        )
    )


def _validate_results_shape(
    payload: dict[str, Any],
) -> None:
    """Reject response structures that do not contain recognized results."""

    if "results" not in payload:
        raise QlooError(
            "Qloo returned an unexpected 'results' format; "
            "the response was not treated as data."
        )

    results = payload["results"]

    if isinstance(results, list):
        return

    if isinstance(results, dict):
        for key in ("entities", "tags"):
            if key in results:
                if isinstance(results[key], list):
                    return

                raise QlooError(
                    "Qloo returned an unexpected 'results' format: "
                    f"'{key}' must be a list."
                )

    raise QlooError(
        "Qloo returned an unexpected 'results' format; "
        "the response was not treated as data."
    )


def _entity_results(
    payload: dict[str, Any],
) -> list[Any]:
    """Extract a result list after response-shape validation."""

    results = payload["results"]

    if isinstance(results, list):
        return results

    if "entities" in results:
        return results["entities"]

    return results["tags"]


class QlooClient:
    """Client for Qloo's entity search and Insights APIs."""

    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()

    def _get_json(
        self,
        url: str,
        params: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        """Send an authenticated GET request and validate its response."""

        api_key = self.settings.qloo_api_key

        if not api_key:
            raise QlooError(
                "QLOO_API_KEY is not configured. "
                "Add your Qloo key to .env."
            )

        requested_at = datetime.now(
            timezone.utc
        ).isoformat()

        headers = CaseInsensitiveDict(
            {
                "x-api-key": api_key,
                "Accept": "application/json",
            }
        )

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.settings.request_timeout,
            )

        except requests.Timeout as exc:
            raise QlooError(
                "Qloo request timed out. Check the connection and retry."
            ) from exc

        except requests.RequestException as exc:
            raise QlooError(
                "Qloo could not be reached. Check your connection and API URL."
            ) from exc

        if response.status_code in (401, 403):
            raise QlooError(
                "Qloo denied access during authentication. "
                "Verify the API key and its permissions.",
                status_code=response.status_code,
            )

        if response.status_code == 429:
            raise QlooError(
                "Qloo rate limit reached. Wait before retrying.",
                status_code=429,
            )

        if response.status_code >= 400:
            raise QlooError(
                f"Qloo returned HTTP {response.status_code}. "
                "Review the request and API access.",
                status_code=response.status_code,
            )

        try:
            payload = response.json()

        except (ValueError, TypeError) as exc:
            raise QlooError(
                "Qloo returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise QlooError(
                "Qloo returned an unexpected response structure."
            )

        _validate_results_shape(payload)

        return payload, requested_at

    def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        take: int = 10,
    ) -> dict[str, Any]:
        """Search Qloo entities by name."""

        cleaned_query = (
            query.strip()
            if isinstance(query, str)
            else ""
        )

        if not cleaned_query:
            raise QlooError(
                "Enter the name of a cultural entity to search for."
            )

        if len(cleaned_query) > 200:
            raise QlooError(
                "Search text must be 200 characters or fewer."
            )

        if (
            not isinstance(take, int)
            or isinstance(take, bool)
            or not 1 <= take <= 20
        ):
            raise QlooError(
                "Search result count must be between 1 and 20."
            )

        if (
            entity_type is not None
            and entity_type not in _SUPPORTED_ENTITY_TYPES
        ):
            raise QlooError(
                "Choose a supported Qloo entity category."
            )

        params: dict[str, Any] = {
            "query": cleaned_query,
            "take": take,
        }

        if entity_type:
            params["types"] = entity_type

        url = _search_url(self.settings.qloo_api_url)

        payload, requested_at = self._get_json(
            url,
            params,
        )

        rows = _entity_results(payload)
        items: list[dict[str, Any]] = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            entity_id = row.get("entity_id") or row.get("id")
            name = row.get("name")

            if (
                not isinstance(entity_id, str)
                or not isinstance(name, str)
            ):
                continue

            item: dict[str, Any] = {
                "id": entity_id,
                "name": name,
            }

            entity_category = row.get("type")

            if isinstance(entity_category, str):
                item["type"] = entity_category

            items.append(item)

        return {
            "status": "live_success",
            "provider": "Qloo API",
            "endpoint": url,
            "requested_at_utc": requested_at,
            "query": cleaned_query,
            "result_count": len(items),
            "items": items,
            "raw_response": payload,
            "provenance_note": (
                "Live entity search response from Qloo. "
                "No entity names or IDs were fabricated."
            ),
        }

    def get_related_entities(
        self,
        entity_urn: str,
        result_type: str,
        take: int = 6,
    ) -> dict[str, Any]:
        """Retrieve related entities using an entity UUID or URN."""

        identifiers = parse_entity_ids(entity_urn)

        if len(identifiers) != 1:
            raise QlooError(
                "Provide exactly one Qloo entity UUID or URN."
            )

        if result_type not in _SUPPORTED_ENTITY_TYPES:
            raise QlooError(
                "Choose a supported Qloo result category, such as "
                "urn:entity:brand, urn:entity:movie, or urn:entity:artist."
            )

        if (
            not isinstance(take, int)
            or isinstance(take, bool)
            or not 1 <= take <= 20
        ):
            raise QlooError(
                "Insight result count must be between 1 and 20."
            )

        params = {
            "filter.type": result_type,
            "signal.interests.entities": identifiers[0],
            "take": take,
        }

        payload, requested_at = self._get_json(
            self.settings.qloo_api_url,
            params,
        )

        rows = _entity_results(payload)
        items: list[dict[str, Any]] = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            entity_id = row.get("entity_id") or row.get("id")
            name = row.get("name")
            item: dict[str, Any] = {}

            if isinstance(entity_id, str):
                item["id"] = entity_id

            if isinstance(name, str):
                item["name"] = name

            entity_category = row.get("type")

            if isinstance(entity_category, str):
                item["type"] = entity_category

            affinity = row.get("affinity")

            if (
                isinstance(affinity, (int, float))
                and not isinstance(affinity, bool)
            ):
                item["affinity"] = affinity

            if item:
                items.append(item)

        return {
            "status": "live_success",
            "provider": "Qloo API",
            "endpoint": self.settings.qloo_api_url,
            "requested_at_utc": requested_at,
            "input_entity_ids": identifiers,
            "input_entity_urns": identifiers,
            "result_type": result_type,
            "result_count": len(items),
            "items": items,
            "raw_response": payload,
            "provenance_note": (
                "Live Qloo Insights response. "
                "Only fields returned by the API are included."
            ),
        }

    def get_cultural_tags(
        self,
        entity_urns: str | list[str] | tuple[str, ...],
    ) -> dict[str, Any]:
        """Retrieve Qloo tag insights for the existing analysis workflow.

        The existing method name is retained for compatibility. Inputs may
        now contain UUID-style Qloo entity IDs or entity URNs.
        """

        identifiers = parse_entity_ids(entity_urns)

        if not identifiers:
            raise QlooError(
                "No Qloo entity identifiers were supplied; "
                "no live request was made."
            )

        params = {
            "filter.type": "urn:tag",
            "signal.interests.entities": ",".join(identifiers),
            "take": 6,
        }

        payload, requested_at = self._get_json(
            self.settings.qloo_api_url,
            params,
        )

        result_block = payload["results"]

        if isinstance(result_block, list):
            rows = result_block
        elif isinstance(result_block, dict):
            rows = result_block.get("tags")

            if not isinstance(rows, list):
                rows = result_block.get("entities")

            if not isinstance(rows, list):
                rows = []
        else:
            raise QlooError(
                "Qloo returned an unexpected 'results' format."
            )

        items: list[dict[str, Any]] = []

        for row in rows:
            if not isinstance(row, dict):
                items.append(
                    {
                        "tag": None,
                        "affinity": None,
                        "raw": row,
                    }
                )
                continue

            tag = row.get("tag")

            if not isinstance(tag, str):
                candidate_name = row.get("name")
                tag = (
                    candidate_name
                    if isinstance(candidate_name, str)
                    else None
                )

            affinity = row.get("affinity")

            if (
                not isinstance(affinity, (int, float))
                or isinstance(affinity, bool)
            ):
                affinity = None

            items.append(
                {
                    "tag": tag,
                    "affinity": affinity,
                    "raw": row,
                }
            )

        return {
            "status": "live_success",
            "provider": "Qloo API",
            "endpoint": self.settings.qloo_api_url,
            "requested_at_utc": requested_at,
            "input_entity_ids": identifiers,
            "input_entity_urns": identifiers,
            "result_count": len(rows),
            "items": items,
            "raw_response": payload,
            "provenance_note": (
                "Live Qloo response. No tag names or affinity values "
                "were fabricated."
            ),
        }