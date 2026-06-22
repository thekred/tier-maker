from __future__ import annotations

import json
import mimetypes
import re
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from paths import cache_root, ensure_data_dirs
from rawg import RawgError, fetch_game_details


def _strip_html(value: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip()


def _game_dir(rawg_id: int) -> Path:
    return cache_root() / str(rawg_id)


def _meta_path(rawg_id: int) -> Path:
    return _game_dir(rawg_id) / "meta.json"


def _find_cover(rawg_id: int) -> Path | None:
    folder = _game_dir(rawg_id)
    if not folder.is_dir():
        return None
    for candidate in sorted(folder.glob("cover.*")):
        if candidate.is_file():
            return candidate
    return None


def cover_public_url(rawg_id: int) -> str | None:
    cover = _find_cover(rawg_id)
    if cover is None:
        return None
    return f"/cache/games/{rawg_id}/{cover.name}"


def load_cached_game(rawg_id: int) -> dict[str, Any] | None:
    meta_path = _meta_path(rawg_id)
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    image_url = cover_public_url(rawg_id)
    if image_url:
        data["image_url"] = image_url
    return data


def _download_cover(url: str, folder: Path) -> str | None:
    request = Request(url, headers={"User-Agent": "TierMaker/1.0"})
    with urlopen(request, timeout=20) as response:
        payload = response.read()
        content_type = response.headers.get("Content-Type", "")
    ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".jpg"
    if ext == ".jpe":
        ext = ".jpg"
    filename = f"cover{ext}"
    (folder / filename).write_bytes(payload)
    return filename


def cache_game(rawg_id: int) -> dict[str, Any]:
    ensure_data_dirs()
    existing = load_cached_game(rawg_id)
    if existing is not None:
        return existing

    details = fetch_game_details(rawg_id)
    game_id = details.get("id")
    if game_id is None:
        raise RawgError("RAWG returned a game without an id")

    folder = _game_dir(int(game_id))
    folder.mkdir(parents=True, exist_ok=True)

    cover_name = None
    image_source = str(details.get("background_image") or "")
    if image_source:
        try:
            cover_name = _download_cover(image_source, folder)
        except Exception:
            cover_name = None

    public_image = f"/cache/games/{game_id}/{cover_name}" if cover_name else ""

    record = {
        "id": game_id,
        "slug": details.get("slug") or "",
        "name": details.get("name") or "Unknown game",
        "description": _strip_html(str(details.get("description") or "")),
        "released": details.get("released") or "",
        "platforms": details.get("platforms") or [],
        "rating": details.get("rating"),
        "metacritic": details.get("metacritic"),
        "image_url": public_image,
        "genres": details.get("genres") or [],
    }
    _meta_path(int(game_id)).write_text(
        json.dumps(record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return record


def resolve_cache_file(relative_path: str) -> Path | None:
    prefix = "/cache/games/"
    if not relative_path.startswith(prefix):
        return None
    tail = relative_path.removeprefix(prefix)
    parts = tail.split("/")
    if len(parts) != 2:
        return None
    rawg_id, filename = parts
    if not rawg_id.isdigit():
        return None
    target = (_game_dir(int(rawg_id)) / filename).resolve()
    root = cache_root().resolve()
    if root not in target.parents or not target.is_file():
        return None
    return target


def enrich_item(item: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(item)
    rawg_id = enriched.get("rawg_id")
    if rawg_id is None:
        enriched.setdefault("cache_ready", False)
        return enriched

    try:
        cached = load_cached_game(int(rawg_id))
    except (TypeError, ValueError):
        enriched.setdefault("cache_ready", False)
        return enriched

    if cached is None:
        enriched.setdefault("cache_ready", False)
        return enriched

    enriched.update(
        {
            "label": enriched.get("label") or cached.get("name") or enriched.get("label"),
            "image_url": cached.get("image_url") or enriched.get("image_url"),
            "platforms": cached.get("platforms") or [],
            "released": cached.get("released") or "",
            "description": cached.get("description") or "",
            "rating": cached.get("rating"),
            "metacritic": cached.get("metacritic"),
            "genres": cached.get("genres") or [],
            "rawg_slug": cached.get("slug") or "",
            "cache_ready": True,
        }
    )
    return enriched


def enrich_board(board: dict[str, Any]) -> dict[str, Any]:
    payload = dict(board)
    items = payload.get("items")
    if isinstance(items, list):
        payload["items"] = [enrich_item(item) for item in items if isinstance(item, dict)]
    return payload
