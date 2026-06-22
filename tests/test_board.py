import unittest

from board import BoardValidationError, Item, Tier, board_from_dict, board_to_dict, new_board


class BoardSerializationTests(unittest.TestCase):
    def test_round_trip_preserves_state(self):
        board = new_board()
        board.title = "Champions"
        board.notes = "Prototype board"
        board.items.extend(
            [
                Item(id="item_1", label="Aatrox", tier_id=board.tiers[0].id, image_url="data:image/svg+xml,one"),
                Item(id="item_2", label="Braum", tier_id=None, image_url="data:image/svg+xml,two"),
            ]
        )

        payload = board_to_dict(board)
        restored = board_from_dict(payload)

        self.assertEqual(restored.title, "Champions")
        self.assertEqual(restored.notes, "Prototype board")
        self.assertEqual([tier.label for tier in restored.tiers], [tier.label for tier in board.tiers])
        self.assertEqual(
            [(item.label, item.tier_id, item.image_url) for item in restored.items],
            [("Aatrox", board.tiers[0].id, "data:image/svg+xml,one"), ("Braum", None, "data:image/svg+xml,two")],
        )

    def test_round_trip_preserves_rawg_id(self):
        board = new_board()
        board.items.append(
            Item(
                id="item_1",
                label="Demo",
                tier_id=None,
                image_url="/cache/games/42/cover.jpg",
                rawg_id=42,
                rawg_slug="demo-game",
                platforms=["PC", "PlayStation 4"],
                released="2020-01-15",
                rating=4.5,
                metacritic=88,
                description="A demo title",
                genres=["Action", "Adventure"],
                cache_ready=True,
            )
        )

        payload = board_to_dict(board)
        restored = board_from_dict(payload)

        self.assertEqual(restored.items[0].rawg_id, 42)
        self.assertEqual(restored.items[0].rawg_slug, "demo-game")
        self.assertEqual(restored.items[0].platforms, ["PC", "PlayStation 4"])
        self.assertEqual(restored.items[0].released, "2020-01-15")
        self.assertEqual(restored.items[0].rating, 4.5)
        self.assertEqual(restored.items[0].metacritic, 88)
        self.assertEqual(restored.items[0].description, "A demo title")
        self.assertEqual(restored.items[0].genres, ["Action", "Adventure"])
        self.assertTrue(restored.items[0].cache_ready)
        self.assertEqual(restored.items[0].image_url, "/cache/games/42/cover.jpg")

    def test_rejects_unknown_tier_reference(self):
        payload = {
            "title": "Bad board",
            "tiers": [{"id": "tier_1", "label": "S", "color": "#ff0000"}],
            "items": [{"id": "item_1", "label": "Example", "tier_id": "missing"}],
        }

        with self.assertRaises(BoardValidationError):
            board_from_dict(payload)

    def test_rejects_duplicate_ids(self):
        payload = {
            "title": "Bad board",
            "tiers": [
                {"id": "tier_1", "label": "S", "color": "#ff0000"},
                {"id": "tier_1", "label": "A", "color": "#00ff00"},
            ],
            "items": [],
        }

        with self.assertRaises(BoardValidationError):
            board_from_dict(payload)


if __name__ == "__main__":
    unittest.main()
