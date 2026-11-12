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

    def test_default_dry_run(self):
        self.assertTrue(main.DRY_RUN)


if __name__ == "__main__":
    unittest.main()
