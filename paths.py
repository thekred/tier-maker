from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def bundle_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def data_root() -> Path:
    if is_frozen():
        # When packaged as an executable, keep runtime data (board, cache, keys)
        # next to the executable in a dedicated folder created on first run.
        exe_parent = Path(sys.executable).resolve().parent
        return exe_parent / "tier-maker-data"
    return Path(__file__).resolve().parent


def static_dir() -> Path:
    return bundle_root() / "static"


def board_file() -> Path:
    return data_root() / "board.json"


def cache_root() -> Path:
    return data_root() / "cache" / "games"


def ensure_data_dirs() -> None:
    data_root().mkdir(parents=True, exist_ok=True)
    cache_root().mkdir(parents=True, exist_ok=True)
