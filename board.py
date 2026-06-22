from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4


DEFAULT_TIER_TEMPLATE = [
    ("S", "#ef4444"),
    ("A", "#f97316"),
    ("B", "#eab308"),
    ("C", "#22c55e"),
    ("D", "#3b82f6"),
    ("F", "#64748b"),
]


class BoardValidationError(ValueError):
    pass


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


@dataclass(slots=True)
class Tier:
    id: str
    label: str
    color: str


@dataclass(slots=True)
class Item:
    id: str
    label: str
    tier_id: Optional[str] = None
    image_url: Optional[str] = None
    rawg_id: Optional[int] = None
    rawg_slug: Optional[str] = None
    platforms: list[str] = field(default_factory=list)
    released: str = ""
    rating: Optional[float] = None
    metacritic: Optional[int] = None
    description: str = ""
    genres: list[str] = field(default_factory=list)
    cache_ready: bool = False


@dataclass(slots=True)
class BoardState:
    title: str
    tiers: list[Tier] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    notes: str = ""


def new_board(title: str = "My Tier List") -> BoardState:
    return BoardState(
        title=title,
        tiers=[Tier(id=_uid("tier"), label=label, color=color) for label, color in DEFAULT_TIER_TEMPLATE],
    )


def board_to_dict(board: BoardState) -> dict[str, Any]:
    return {
        "title": board.title,
        "notes": board.notes,
        "tiers": [
            {"id": tier.id, "label": tier.label, "color": tier.color}
            for tier in board.tiers
        ],
        "items": [
            {
                "id": item.id,
                "label": item.label,
                "tier_id": item.tier_id,
                "image_url": item.image_url,
                **({"rawg_id": item.rawg_id} if item.rawg_id is not None else {}),
                **({"rawg_slug": item.rawg_slug} if item.rawg_slug is not None else {}),
                "platforms": item.platforms,
                "released": item.released,
                "rating": item.rating,
                "metacritic": item.metacritic,
                "description": item.description,
                "genres": item.genres,
                "cache_ready": item.cache_ready,
            }
            for item in board.items
        ],
    }


def _require_string(data: dict[str, Any], key: str, fallback: str = "") -> str:
    value = data.get(key, fallback)
    if not isinstance(value, str):
        raise BoardValidationError(f"{key} must be a string")
    return value


def _validate_hex_color(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        raise BoardValidationError("tier color must be a hex string like #ff00aa")
    allowed = "0123456789abcdefABCDEF"
    if any(ch not in allowed for ch in value[1:]):
        raise BoardValidationError("tier color must be a hex string like #ff00aa")
    return value.lower()


def board_from_dict(data: Any) -> BoardState:
    if not isinstance(data, dict):
        raise BoardValidationError("board data must be an object")

    title = _require_string(data, "title", "My Tier List")
    notes = _require_string(data, "notes", "")

    raw_tiers = data.get("tiers", [])
    if not isinstance(raw_tiers, list):
        raise BoardValidationError("tiers must be a list")

    tiers: list[Tier] = []
    seen_tier_ids: set[str] = set()
    for raw in raw_tiers:
        if not isinstance(raw, dict):
            raise BoardValidationError("each tier must be an object")
        tier_id = _require_string(raw, "id")
        label = _require_string(raw, "label", tier_id)
        color = _validate_hex_color(raw.get("color", "#64748b"))
        if tier_id in seen_tier_ids:
            raise BoardValidationError("tier ids must be unique")
        seen_tier_ids.add(tier_id)
        tiers.append(Tier(id=tier_id, label=label, color=color))

    raw_items = data.get("items", [])
    if not isinstance(raw_items, list):
        raise BoardValidationError("items must be a list")

    items: list[Item] = []
    seen_item_ids: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise BoardValidationError("each item must be an object")
        item_id = _require_string(raw, "id")
        label = _require_string(raw, "label", item_id)
        tier_id = raw.get("tier_id")
        image_url = raw.get("image_url")
        rawg_id = raw.get("rawg_id")
        rawg_slug = raw.get("rawg_slug")
        platforms = raw.get("platforms", [])
        released = _require_string(raw, "released", "")
        rating = raw.get("rating")
        metacritic = raw.get("metacritic")
        description = _require_string(raw, "description", "")
        genres = raw.get("genres", [])
        cache_ready = raw.get("cache_ready", False)

        if tier_id is not None and not isinstance(tier_id, str):
            raise BoardValidationError("item tier_id must be a string or null")
        if image_url is not None and not isinstance(image_url, str):
            raise BoardValidationError("item image_url must be a string or null")
        if rawg_id is not None:
            if isinstance(rawg_id, bool):
                raise BoardValidationError("item rawg_id must be an integer or null")
            if not isinstance(rawg_id, int):
                try:
                    rawg_id = int(rawg_id)
                except (TypeError, ValueError) as exc:
                    raise BoardValidationError("item rawg_id must be an integer or null") from exc
        if rawg_slug is not None and not isinstance(rawg_slug, str):
            raise BoardValidationError("item rawg_slug must be a string or null")
        if not isinstance(platforms, list) or any(not isinstance(entry, str) for entry in platforms):
            raise BoardValidationError("item platforms must be a list of strings")
        if not isinstance(genres, list) or any(not isinstance(entry, str) for entry in genres):
            raise BoardValidationError("item genres must be a list of strings")
        if cache_ready is None:
            cache_ready = False
        if not isinstance(cache_ready, bool):
            raise BoardValidationError("item cache_ready must be a boolean")
        if rating is not None and not isinstance(rating, (int, float)):
            raise BoardValidationError("item rating must be a number or null")
        if metacritic is not None and isinstance(metacritic, bool):
            raise BoardValidationError("item metacritic must be an integer or null")
        if metacritic is not None and not isinstance(metacritic, int):
            try:
                metacritic = int(metacritic)
            except (TypeError, ValueError) as exc:
                raise BoardValidationError("item metacritic must be an integer or null") from exc
        if tier_id is not None and tier_id not in seen_tier_ids:
            raise BoardValidationError(f"unknown tier_id: {tier_id}")
        if item_id in seen_item_ids:
            raise BoardValidationError("item ids must be unique")
        seen_item_ids.add(item_id)
        items.append(
            Item(
                id=item_id,
                label=label,
                tier_id=tier_id,
                image_url=image_url,
                rawg_id=rawg_id,
                rawg_slug=rawg_slug,
                platforms=platforms,
                released=released,
                rating=rating,
                metacritic=metacritic,
                description=description,
                genres=genres,
                cache_ready=cache_ready,
            )
        )

    return BoardState(title=title, tiers=tiers, items=items, notes=notes)


def board_from_json(text: str) -> BoardState:
    import json

    data = json.loads(text)
    return board_from_dict(data)


def board_to_json(board: BoardState, *, indent: int = 2) -> str:
    import json

    return json.dumps(board_to_dict(board), indent=indent, ensure_ascii=False)


def default_board_json() -> str:
    return board_to_json(new_board())
