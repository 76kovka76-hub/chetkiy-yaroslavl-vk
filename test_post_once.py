"""Post exactly one real, friendly VK connection test and record it in history."""
from datetime import datetime, timezone
import logging

from main import GROUP_ID, history_load, history_save, format_message, post_vk, slot

TEST_KEY = "connection_test_first_2026"
TEST_DRAFT = {
    "publish": True,
    "sentence": "👋 Братва, проверяем связь — кто из какого района Ярославля, пишите в комменты!",
    "hashtags": ["#ЯрославльНаСвязи", "#ЯрославльЗнакомимся", "#ЯрославльНашЧат"],
}


def main():
    now = datetime.now(timezone.utc)
    current_slot = slot(now)
    history = history_load()
    if any(p.get("game_key") == TEST_KEY for p in history["posts"]):
        logging.info("Тестовая публикация уже была отправлена: повторов не будет.")
        return
    if any(p.get("slot") == current_slot for p in history["posts"]):
        logging.info("В этом временном слоте уже есть публикация — тест не дублируем.")
        return
    message = format_message(TEST_DRAFT, history)
    if not message:
        raise RuntimeError("Тестовая публикация не прошла проверку формата или новые хэштеги уже использовались")
    post_id = post_vk(message, "one-time-connection-test-2026")
    history["posts"].append({
        "slot": current_slot, "post_id": post_id, "kind": "game", "game_key": TEST_KEY,
        "title": "Проверка связи", "text": TEST_DRAFT["sentence"],
        "published_at": now.isoformat()
    })
    history["used_tags"].extend(TEST_DRAFT["hashtags"])
    history_save(history)
    logging.info("ТЕСТОВЫЙ ПОСТ ОПУБЛИКОВАН: https://vk.com/wall-%s_%s", GROUP_ID, post_id)


if __name__ == "__main__":
    main()
