from __future__ import annotations

import json
import os
from functools import lru_cache
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


from paths import data_root


ROOT = Path(__file__).resolve().parent
RAWG_API_BASE = "https://api.rawg.io/api"

# Parent platform IDs from RAWG: PC, PlayStation, Xbox, Mac, Linux, Nintendo.
ALLOWED_PARENT_PLATFORMS = "1,2,3,6,7,8"

_EXCLUDED_PLATFORM_TOKENS = ("web", "ios", "android")

_CONSOLE_OR_PC_TOKENS = (
    "pc",
    "linux",
    "mac",
    "windows",
    "playstation",
    "ps ",
    "psvita",
    "ps vita",
    "psp",
    "xbox",
    "nintendo",
    "switch",
    "wii",
    "game boy",
    "gameboy",
    "3ds",
    " ds",
    "nes",
    "snes",
    "n64",
    "gamecube",
    "genesis",
    "mega drive",
    "dreamcast",
    "saturn",
    "atari",
    "commodore",
    "amiga",
    "sega",
    "neo geo",
    "turbografx",
)


class RawgError(RuntimeError):
    pass


def _read_api_key() -> str:
    env_key = os.environ.get("RAWG_API_KEY", "").strip()
    if env_key:
        return env_key

    key_file = data_root() / ".rawg_key"
    if key_file.exists():
        value = key_file.read_text(encoding="utf-8").strip()
        if value:
            return value

    legacy_key_file = ROOT / ".rawg_key"
    if legacy_key_file.exists():
        value = legacy_key_file.read_text(encoding="utf-8").strip()
        if value:
            return value

    raise RawgError("RAWG API key is missing. Set RAWG_API_KEY or create a .rawg_key file.")


def _fetch_json(url: str, timeout: float = 10.0) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "TierMaker/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        raise RawgError(str(exc)) from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RawgError("RAWG returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise RawgError("RAWG returned unexpected payload")
    return data


def _is_excluded_platform(name: str) -> bool:
    lower = name.lower()
    return any(token in lower for token in _EXCLUDED_PLATFORM_TOKENS)


def _is_console_or_pc_platform(name: str) -> bool:
    if _is_excluded_platform(name):
        return False
    lower = f" {name.lower()} "
    return any(token in lower for token in _CONSOLE_OR_PC_TOKENS)


def _collect_platform_names(entry: dict[str, Any]) -> list[str]:
    platforms: list[str] = []
    for platform_entry in entry.get("platforms") or []:
        if not isinstance(platform_entry, dict):
            continue
        platform = platform_entry.get("platform")
        if isinstance(platform, dict):
            name = platform.get("name")
            if isinstance(name, str) and name and not _is_excluded_platform(name):
                platforms.append(name)
    return platforms


def _game_is_console_or_pc(entry: dict[str, Any]) -> bool:
    for platform_entry in entry.get("platforms") or []:
        if not isinstance(platform_entry, dict):
            continue
        platform = platform_entry.get("platform")
        if not isinstance(platform, dict):
            continue
        name = platform.get("name")
        if isinstance(name, str) and _is_console_or_pc_platform(name):
            return True
    return False


def _normalize_game(entry: dict[str, Any]) -> dict[str, Any]:
    platforms = _collect_platform_names(entry)

    return {
        "id": entry.get("id"),
        "slug": entry.get("slug") or "",
        "name": entry.get("name") or "Unknown game",
        "name_original": entry.get("name_original") or entry.get("name") or "Unknown game",
        "background_image": entry.get("background_image") or "",
        "released": entry.get("released") or "",
        "rating": entry.get("rating"),
        "metacritic": entry.get("metacritic"),
        "platforms": platforms,
        "added": entry.get("added"),
        "updated": entry.get("updated"),
        "created": entry.get("created"),
    }


def _normalize_game_detail(entry: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_game(entry)
    description = entry.get("description")
    payload["description"] = description if isinstance(description, str) else ""
    # Collect genres as a simple list of names when available
    genres: list[str] = []
    for g in entry.get("genres") or []:
        if isinstance(g, dict):
            name = g.get("name")
            if isinstance(name, str) and name:
                genres.append(name)
    payload["genres"] = genres
    return payload


@lru_cache(maxsize=256)
def fetch_game_details(game_id: int) -> dict[str, Any]:
    key = _read_api_key()
    params = urlencode({"key": key})
    payload = _fetch_json(f"{RAWG_API_BASE}/games/{game_id}?{params}")
    if not isinstance(payload, dict):
        raise RawgError("RAWG returned unexpected game payload")
    return _normalize_game_detail(payload)


def _normalize_text(value: str) -> str:
    return " ".join(
        token
        for token in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
        if token
    )


def _query_tokens(query: str) -> list[str]:
    return [token for token in _normalize_text(query).split() if token]


def _matches_query(game: dict[str, Any], query_tokens: list[str]) -> bool:
    if not query_tokens:
        return True

    haystack_parts = [
        str(game.get("name") or ""),
        str(game.get("name_original") or ""),
        str(game.get("slug") or ""),
    ]
    haystack = _normalize_text(" ".join(haystack_parts))
    return all(token in haystack for token in query_tokens)


def _release_date_value(value: str) -> date:
    if not value:
        return date.min
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return date.min


@lru_cache(maxsize=128)
def search_games(query: str, page_size: int = 40, max_pages: int = 3) -> list[dict[str, Any]]:
    cleaned = query.strip()
    if not cleaned:
        return []

    key = _read_api_key()
    normalized_by_id: dict[Any, dict[str, Any]] = {}
    query_tokens = _query_tokens(cleaned)
    page = 1

    while page <= max_pages:
        params = urlencode(
            {
                "key": key,
                "search": cleaned,
                "search_precise": "true",
                "parent_platforms": ALLOWED_PARENT_PLATFORMS,
                "page_size": page_size,
                "page": page,
            }
        )
        payload = _fetch_json(f"{RAWG_API_BASE}/games?{params}")
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise RawgError("RAWG returned unexpected results")

        for entry in results:
            if isinstance(entry, dict) and _game_is_console_or_pc(entry):
                normalized = _normalize_game(entry)
                game_id = normalized.get("id")
                if game_id is not None and _matches_query(normalized, query_tokens):
                    normalized_by_id[game_id] = normalized

        if not payload.get("next"):
            break
        page += 1

    return sorted(
        normalized_by_id.values(),
        key=lambda game: (
            -_release_date_value(str(game.get("released") or "")).toordinal(),
            str(game.get("name") or ""),
        ),
    )
