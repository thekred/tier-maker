from __future__ import annotations

import argparse
import base64
import io
import json
import mimetypes
import os
import shutil
import tempfile
import threading
import webbrowser
import zipfile
from copy import deepcopy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from board import BoardValidationError, board_from_json, board_to_dict, new_board
from game_cache import cache_game, enrich_board, resolve_cache_file
from paths import board_file, ensure_data_dirs, static_dir
from rawg import RawgError, search_games


ensure_data_dirs()
STATIC_DIR = static_dir()
DATA_FILE = board_file()


class AppState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._board = self._load_from_disk()

    def _load_from_disk(self):
        if DATA_FILE.exists():
            try:
                return board_from_json(DATA_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, BoardValidationError):
                pass
        return new_board()

    def get_board(self):
        with self._lock:
            return self._board

    def set_board(self, board):
        with self._lock:
            self._board = board
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            DATA_FILE.write_text(json.dumps(board_to_dict(board), indent=2, ensure_ascii=False), encoding="utf-8")


STATE = AppState()


def _send_json(handler: BaseHTTPRequestHandler, payload, status: HTTPStatus = HTTPStatus.OK):
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _serve_file(handler: BaseHTTPRequestHandler, path: Path):
    if not path.exists() or not path.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
        return

    mime_type, _ = mimetypes.guess_type(str(path))
    body = path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", mime_type or "application/octet-stream")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _safe_export_name(title: str) -> str:
    cleaned = "".join(ch for ch in title.strip() if ch not in '<>:"/\\|?*').strip()
    return cleaned or "tier-list"


def _resolve_static_path(path: str) -> Path | None:
    if path in {"/", "/index.html"}:
        return STATIC_DIR / "index.html"
    if path in {"/styles.css", "/app.js"}:
        return STATIC_DIR / path.lstrip("/")
    if path.startswith("/static/"):
        rel = unquote(path.removeprefix("/static/"))
        return (STATIC_DIR / rel).resolve()
    return None


def build_tier_archive(board: dict[str, Any]) -> bytes:
    payload = deepcopy(board)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        items = payload.get("items", [])
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                img = item.get("image_url") or ""
                if img.startswith("/cache/games/"):
                    target = resolve_cache_file(img)
                    if target and target.is_file():
                        ext = Path(target.name).suffix or ".bin"
                        arcname = f"images/{item.get('id')}{ext}"
                        try:
                            zf.write(target, arcname)
                            item["image_url"] = arcname
                        except Exception:
                            pass
                elif img.startswith("data:"):
                    try:
                        header, b64 = img.split(",", 1)
                        mime = header.split(";")[0].split(":", 1)[1]
                        ext = mimetypes.guess_extension(mime) or ".bin"
                        arcname = f"images/{item.get('id')}{ext}"
                        zf.writestr(arcname, base64.b64decode(b64))
                        item["image_url"] = arcname
                    except Exception:
                        pass
        zf.writestr("board.json", json.dumps(payload, ensure_ascii=False, indent=2))
    mem.seek(0)
    return mem.read()


def _extract_multipart_file(content_type: str, body: bytes, field_name: str = "file") -> tuple[str | None, bytes | None]:
    from email.parser import BytesParser
    from email.policy import HTTP

    headers = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
    message = BytesParser(policy=HTTP).parsebytes(headers + body)
    if not message.is_multipart():
        return None, None

    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        if part.get_param("name", header="content-disposition") != field_name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        return filename, payload or b""

    return None, None


class TierMakerHandler(BaseHTTPRequestHandler):
    server_version = "TierMaker/0.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        cache_target = resolve_cache_file(parsed.path)
        if cache_target is not None:
            return _serve_file(self, cache_target)

        target = _resolve_static_path(parsed.path)
        if target is not None:
            if target != (STATIC_DIR / "index.html").resolve():
                static_root = STATIC_DIR.resolve()
                if static_root not in target.parents and target != static_root:
                    self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
                    return
            return _serve_file(self, target)
        if parsed.path == "/api/state":
            return _send_json(self, enrich_board(board_to_dict(STATE.get_board())))
        if parsed.path == "/api/export":
            board = board_to_dict(STATE.get_board())
            filename = f"{_safe_export_name(board.get('title', 'tier-list'))}.json"
            body = json.dumps(board, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/export_tier":
            board = board_to_dict(STATE.get_board())
            body = build_tier_archive(board)
            fname = f"{_safe_export_name(board.get('title','tier-list'))}.tier"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/rawg/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            try:
                results = search_games(query)
            except RawgError as exc:
                return _send_json(self, {"ok": False, "error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return _send_json(self, {"ok": True, "results": results})
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        content_type = self.headers.get("Content-Type", "")
        raw_body = ""
        raw_data = b""
        if not content_type.startswith("multipart/form-data"):
            raw_data = self.rfile.read(content_length) if content_length else b""
            if raw_data:
                try:
                    raw_body = raw_data.decode("utf-8")
                except UnicodeDecodeError:
                    raw_body = ""

        if parsed.path == "/api/rawg/cache":
            try:
                payload = json.loads(raw_body) if raw_body else {}
            except json.JSONDecodeError:
                return _send_json(self, {"ok": False, "error": "Invalid JSON body"}, HTTPStatus.BAD_REQUEST)
            rawg_id = payload.get("rawg_id")
            if rawg_id is None:
                return _send_json(self, {"ok": False, "error": "rawg_id is required"}, HTTPStatus.BAD_REQUEST)
            try:
                game = cache_game(int(rawg_id))
            except (TypeError, ValueError):
                return _send_json(self, {"ok": False, "error": "rawg_id must be an integer"}, HTTPStatus.BAD_REQUEST)
            except RawgError as exc:
                return _send_json(self, {"ok": False, "error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return _send_json(self, {"ok": True, "game": game})

        if parsed.path in {"/api/state", "/api/load"}:
            try:
                board = board_from_json(raw_body)
            except (json.JSONDecodeError, BoardValidationError) as exc:
                return _send_json(self, {"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            STATE.set_board(board)
            return _send_json(
                self,
                {
                    "ok": True,
                    "board": enrich_board(board_to_dict(board)),
                    "save_path": str(DATA_FILE.resolve()),
                },
            )

        if parsed.path == "/api/new":
            board = new_board()
            STATE.set_board(board)
            return _send_json(
                self,
                {
                    "ok": True,
                    "board": enrich_board(board_to_dict(board)),
                    "save_path": str(DATA_FILE.resolve()),
                },
            )

        if parsed.path == "/api/import_tier":
            # Accept a multipart form upload containing a .tier archive
            # and import board.json + images into runtime cache.
            try:
                content_type = self.headers.get("Content-Type", "")
                if not content_type.startswith("multipart/form-data"):
                    return _send_json(self, {"ok": False, "error": "Expected multipart/form-data"}, HTTPStatus.BAD_REQUEST)

                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length) if content_length else b""
                filename, data = _extract_multipart_file(content_type, body)
                if data is None:
                    return _send_json(self, {"ok": False, "error": "No file uploaded"}, HTTPStatus.BAD_REQUEST)

                with tempfile.TemporaryDirectory() as tmpname:
                    tmpdir = Path(tmpname)
                    with zipfile.ZipFile(io.BytesIO(data)) as zf:
                        zf.extractall(tmpdir)

                    board_path = tmpdir / "board.json"
                    if not board_path.exists():
                        return _send_json(self, {"ok": False, "error": "Archive missing board.json"}, HTTPStatus.BAD_REQUEST)
                    board = json.loads(board_path.read_text(encoding="utf-8"))

                    # Move any images into cache_root under an import folder and rewrite image_url
                    from paths import cache_root
                    import uuid

                    images_dir = tmpdir / "images"
                    id_map: dict[str, str] = {}
                    if images_dir.exists() and images_dir.is_dir():
                        for img in images_dir.iterdir():
                            foldername = f"imported-{uuid.uuid4().hex}"
                            new_folder = cache_root() / foldername
                            new_folder.mkdir(parents=True, exist_ok=True)
                            dest = new_folder / img.name
                            try:
                                shutil.move(str(img), str(dest))
                                id_map[img.name] = f"/cache/games/{foldername}/{dest.name}"
                            except Exception:
                                pass

                    # Rewrite image urls for items that referenced images/<name>
                    for item in board.get("items", []):
                        img = item.get("image_url") or ""
                        if img.startswith("images/"):
                            name = img.split("/", 1)[1]
                            if name in id_map:
                                item["image_url"] = id_map[name]

                    STATE.set_board(board_from_json(json.dumps(board)))
                    return _send_json(self, {"ok": True, "board": enrich_board(board)})
            except Exception as exc:
                return _send_json(self, {"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), TierMakerHandler)
    url = f"http://{host}:{server.server_port}/"
    print(f"Tier Maker running at {url}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def parse_args():
    parser = argparse.ArgumentParser(description="Local tier list editor prototype")
    parser.add_argument("--host", default=os.environ.get("TIER_MAKER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("TIER_MAKER_PORT", "8000")))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.host, args.port)
