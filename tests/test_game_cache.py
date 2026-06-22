import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from game_cache import enrich_item, load_cached_game
from paths import cache_root


class GameCacheTests(unittest.TestCase):
    def test_enrich_item_uses_cached_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cache" / "games" / "42"
            root.mkdir(parents=True)
            (root / "meta.json").write_text(
                json.dumps(
                    {
                        "id": 42,
                        "slug": "demo-game",
                        "name": "Demo Game",
                        "description": "Cached description",
                        "released": "2020-01-15",
                        "platforms": ["PC", "PlayStation 4"],
                        "rating": 4.2,
                        "metacritic": 88,
                        "image_url": "/cache/games/42/cover.jpg",
                    }
                ),
                encoding="utf-8",
            )
            (root / "cover.jpg").write_bytes(b"fake-image")

            with patch("game_cache.cache_root", return_value=Path(tmp) / "cache" / "games"):
                enriched = enrich_item(
                    {
                        "id": "item_1",
                        "label": "Demo Game",
                        "tier_id": None,
                        "image_url": "/cache/games/42/cover.jpg",
                        "rawg_id": 42,
                    }
                )

        self.assertTrue(enriched["cache_ready"])
        self.assertEqual(enriched["description"], "Cached description")
        self.assertEqual(enriched["platforms"], ["PC", "PlayStation 4"])
        self.assertEqual(enriched["released"], "2020-01-15")

    def test_load_cached_game_missing_returns_none(self):
        with patch("game_cache.cache_root", return_value=cache_root()):
            self.assertIsNone(load_cached_game(999999999))


if __name__ == "__main__":
    unittest.main()
