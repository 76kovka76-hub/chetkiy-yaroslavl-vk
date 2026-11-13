import unittest
from datetime import datetime, timedelta, timezone
import main
from engagement import game_draft, MAX_GAMES_PER_DAY


class NewsBotTests(unittest.TestCase):
    def test_correct_vk_group(self):
        self.assertEqual(main.GROUP_ID, "243223029")

    def test_thirty_slots_per_day(self):
        keys = set()
        start = datetime(2026, 11, 11, 21, tzinfo=timezone.utc)  # Moscow 00:00
        for minute in range(24 * 60):
            keys.add(main.slot(start + timedelta(minutes=minute)))
        self.assertEqual(len(keys), 30)
        self.assertEqual(sorted(keys), [f"2026-11-12-{i:02d}" for i in range(30)])

    def test_url_tracking_removes_parameters(self):
        a = main.url_key("https://www.example.ru/news/story/?utm_source=vk")
        b = main.url_key("https://example.ru/news/story")
        self.assertEqual(a, b)

    def test_reworded_duplicate_title(self):
        a = "В Ярославле перекроют движение на улице Ленина"
        b = "В Ярославле на улице Ленина перекроют движение"
        self.assertTrue(main.title_duplicate(a, b))

    def test_topic_tags_and_reuse(self):
        draft = {
            "publish": True,
            "sentence": "🚧 Братва, на Ленинградском проспекте временно ограничат движение.",
            "hashtags": ["#ЯрославльДороги", "#ПробкиЯрославля", "#РемонтЯрославль"],
        }
        h = {"used_tags": []}
        result = main.format_message(draft, h)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.split("\n\n")[1].split()), 3)
        h["used_tags"] = ["#ЯрославльДороги"]
        self.assertIsNotNone(main.format_message(draft, h))

    def test_reject_non_yaroslavl_hashtags(self):
        bad = {
            "publish": True,
            "sentence": "🚧 Народ, ремонт дороги начался.",
            "hashtags": ["#Москва", "#Дороги", "#Ремонт"],
        }
        self.assertIsNone(main.format_message(bad, {"used_tags": []}))

    def test_reject_numeric_and_synthetic_hashtags(self):
        for bad_tag in ("#ЯрославльНовости2026", "#ЯрославльДороги_42", "#ЯрославльДороги_abc"):
            with self.subTest(tag=bad_tag):
                draft = {
                    "publish": True,
                    "sentence": "🏙️ Народ, новости Ярославля.",
                    "hashtags": [bad_tag, "#ЯрославльГород", "#ЯрославльСобытия"],
                }
                self.assertIsNone(main.format_message(draft, {"used_tags": []}))

    def test_offline_post_has_real_headline_and_three_tags(self):
        item = {"title": "В Ярославле перекроют дорогу на улице Ленина из-за ремонта",
                "link": "https://example.com/story/42"}
        history = {"posts": [], "used_tags": []}
        draft = main.offline_draft(item, history)
        self.assertTrue(draft["publish"])
        self.assertIn("Ярославле перекроют дорогу", draft["sentence"])
        self.assertEqual(len(draft["hashtags"]), 3)
        self.assertIsNotNone(main.format_message(draft, history))

    def test_regional_news_does_not_automatically_become_city_news(self):
        item = {"title": "В Ярославской области открыли новую дорогу за городом",
                "link": "https://example.com/region"}
        self.assertFalse(main.offline_draft(item, {"posts": [], "used_tags": []})["publish"])

    def test_offline_tags_remain_clean_after_reuse(self):
        item = {"title": "В Ярославле открыли ремонтируемый участок дороги для машин",
                "link": "https://example.com/local/22"}
        history = {"posts": [], "used_tags": []}
        first = main.offline_draft(item, history)
        self.assertTrue(first["publish"])
        history["used_tags"] = first["hashtags"]
        second = main.offline_draft(item, history)
        self.assertTrue(second["publish"])
        self.assertEqual(first["hashtags"], second["hashtags"])
        self.assertTrue(all(tag[1:].isalpha() for tag in second["hashtags"]))
        self.assertIsNotNone(main.format_message(second, history))

    def test_game_prompt_can_replace_missing_news(self):
        now = datetime(2026, 11, 12, 9, 15, tzinfo=timezone.utc)  # 12:15 Moscow
        h = {"posts": [], "used_tags": []}
        game = game_draft(h, now)
        self.assertIsNotNone(game)
        self.assertTrue(any(word in game["sentence"].casefold() for word in ("братва", "пацаны", "народ", "родные")))
        self.assertEqual(len(game["hashtags"]), 3)
        self.assertIsNotNone(main.format_message(game, h))

    def test_game_not_sent_at_night(self):
        now = datetime(2026, 11, 12, 1, 0, tzinfo=timezone.utc)  # 04:00 Moscow
        self.assertIsNone(game_draft({"posts": [], "used_tags": []}, now))

    def test_game_daily_limit(self):
        now = datetime(2026, 11, 12, 18, tzinfo=timezone.utc)  # 21:00 Moscow
        game_posts = [{"kind": "game", "slot": f"2026-11-12-{i:02d}",
                       "game_key": f"some_{i}",
                       "published_at": datetime(2026, 11, 12, i, tzinfo=timezone.utc).isoformat()}
                      for i in range(MAX_GAMES_PER_DAY)]
        self.assertIsNone(game_draft({"posts": game_posts, "used_tags": []}, now))

    def test_game_cooldown(self):
        now = datetime(2026, 11, 12, 9, 15, tzinfo=timezone.utc)
        game_posts = [{"kind": "game", "slot": "2026-11-12-15",
                       "game_key": "introductions",
                       "published_at": (now - timedelta(minutes=45)).isoformat()}]
        self.assertIsNone(game_draft({"posts": game_posts, "used_tags": []}, now))

    def test_game_no_repeat_with_readable_hashtags(self):
        now = datetime(2026, 11, 12, 9, 15, tzinfo=timezone.utc)
        h = {"posts": [], "used_tags": []}
        first = game_draft(h, now)
        h["posts"] = [{"kind": "game", "slot": "2026-11-12-00",
                       "game_key": first["game_key"],
                       "published_at": (now - timedelta(days=1)).isoformat()}]
        h["used_tags"] = first["hashtags"]
        second = game_draft(h, now)
        self.assertIsNotNone(second)
        self.assertNotEqual(first["game_key"], second["game_key"])
        self.assertTrue(all(tag[1:].isalpha() for tag in second["hashtags"]))
        self.assertIsNotNone(main.format_message(second, h))

    def test_default_dry_run(self):
        self.assertTrue(main.DRY_RUN)


if __name__ == "__main__":
    unittest.main()
