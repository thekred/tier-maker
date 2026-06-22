import unittest

from rawg import (
    _game_is_console_or_pc,
    _is_console_or_pc_platform,
    _is_excluded_platform,
    _matches_query,
    _normalize_game,
    _query_tokens,
    _release_date_value,
)


class RawgSearchTests(unittest.TestCase):
    def test_query_tokens_split_words(self):
        self.assertEqual(_query_tokens("  Red Dead  "), ["red", "dead"])

    def test_matches_query_requires_all_tokens(self):
        game = {"name": "Nyakuza Metro", "name_original": "Nyakuza Metro", "slug": "nyakuza-metro"}
        self.assertTrue(_matches_query(game, _query_tokens("yakuza")))
        self.assertFalse(_matches_query({"name": "Sakura Wars", "slug": "sakura-wars"}, _query_tokens("yakuza")))

    def test_release_date_sorting_is_newest_first(self):
        dates = ["2001-01-01", "2020-05-10", "2012-12-12"]
        ordered = sorted(dates, key=lambda value: -_release_date_value(value).toordinal())
        self.assertEqual(ordered, ["2020-05-10", "2012-12-12", "2001-01-01"])

    def test_excluded_platforms(self):
        self.assertTrue(_is_excluded_platform("Web"))
        self.assertTrue(_is_excluded_platform("iOS"))
        self.assertTrue(_is_excluded_platform("Android"))
        self.assertFalse(_is_excluded_platform("PC"))

    def test_console_or_pc_platform_detection(self):
        self.assertTrue(_is_console_or_pc_platform("PlayStation 5"))
        self.assertTrue(_is_console_or_pc_platform("PC"))
        self.assertFalse(_is_console_or_pc_platform("Web"))
        self.assertFalse(_is_console_or_pc_platform("iOS"))

    def test_game_is_console_or_pc(self):
        pc_game = {"platforms": [{"platform": {"name": "PC"}}]}
        web_game = {"platforms": [{"platform": {"name": "Web"}}]}
        mixed_game = {
            "platforms": [
                {"platform": {"name": "Web"}},
                {"platform": {"name": "PlayStation 4"}},
            ]
        }
        self.assertTrue(_game_is_console_or_pc(pc_game))
        self.assertFalse(_game_is_console_or_pc(web_game))
        self.assertTrue(_game_is_console_or_pc(mixed_game))

    def test_normalize_game_strips_web_platform(self):
        normalized = _normalize_game(
            {
                "id": 1,
                "name": "Example",
                "platforms": [
                    {"platform": {"name": "Web"}},
                    {"platform": {"name": "PC"}},
                ],
            }
        )
        self.assertEqual(normalized["platforms"], ["PC"])


if __name__ == "__main__":
    unittest.main()
