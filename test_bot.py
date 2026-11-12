import unittest
from datetime import datetime, timedelta, timezone
import main


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
        self.assertIsNone(main.format_message(draft, h))

    def test_reject_non_yaroslavl_hashtags(self):
        bad = {
            "publish": True,
            "sentence": "🚧 Народ, ремонт дороги начался.",
            "hashtags": ["#Москва", "#Дороги", "#Ремонт"],
        }
        self.assertIsNone(main.format_message(bad, {"used_tags": []}))

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

    def test_offline_tags_change_if_used(self):
        item = {"title": "В Ярославле открыли ремонтируемый участок дороги для машин",
                "link": "https://example.com/local/22"}
        history = {"posts": [], "used_tags": []}
        first = main.offline_draft(item, history)
        self.assertTrue(first["publish"])
        history["used_tags"] = first["hashtags"]
        second = main.offline_draft(item, history)
        self.assertTrue(second["publish"])
        self.assertFalse(set(first["hashtags"]) & set(second["hashtags"]))

    def test_default_dry_run(self):
        self.assertTrue(main.DRY_RUN)


if __name__ == "__main__":
    unittest.main()
