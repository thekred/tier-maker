import io
import json
import unittest
import zipfile

from board import Item, Tier, board_to_dict, new_board
from main import _extract_multipart_file, build_tier_archive


class MainExportTests(unittest.TestCase):
    def test_build_tier_archive_contains_board_json(self):
        board = new_board()
        board.items.append(
            Item(
                id="item_1",
                label="Demo",
                tier_id=board.tiers[0].id,
                image_url="data:image/png;base64,AAA=",
                rawg_id=42,
                rawg_slug="demo-game",
                platforms=["PC"],
                released="2024-01-01",
                rating=9.1,
                metacritic=95,
                description="Test description",
                genres=["Action"],
                cache_ready=True,
            )
        )

        archive_bytes = build_tier_archive(board_to_dict(board))
        self.assertIsInstance(archive_bytes, (bytes, bytearray))

        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
            self.assertIn("board.json", zf.namelist())
            data = json.loads(zf.read("board.json").decode("utf-8"))
            self.assertEqual(data["title"], board.title)
            self.assertEqual(data["items"][0]["rawg_id"], 42)
            self.assertEqual(data["items"][0]["rawg_slug"], "demo-game")
            self.assertEqual(data["items"][0]["genres"], ["Action"])
            self.assertTrue(any(name.startswith("images/item_1") for name in zf.namelist()))

    def test_extract_multipart_file(self):
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"file\"; filename=\"test.tier\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n"
            "ZIPDATA"
            f"\r\n--{boundary}--\r\n"
        ).encode("utf-8")
        filename, data = _extract_multipart_file(f"multipart/form-data; boundary={boundary}", body)
        self.assertEqual(filename, "test.tier")
        self.assertEqual(data, b"ZIPDATA")


if __name__ == "__main__":
    unittest.main()
