import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone

from config import CLIPS_DIR, DB_PATH, DOWNLOAD_DIR, FINAL_CLIPS_DIR

DB_LOCK = threading.Lock()

DEFAULT_DB = {
    "channel": {
        "url": "",
        "channel_id": "",
        "name": "",
        "added_at": "",
    },
    "last_check": "",
    "settings": {
        "caption_font_size": 24,
        "caption_position": "bottom",
        "caption_color": "white",
        "caption_background": "black@0.5",
        "whisper_model": "base",
        "schedule_time": "09:00",
    },
    "videos": [],
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_directories() -> None:
    for path in (DOWNLOAD_DIR, CLIPS_DIR, FINAL_CLIPS_DIR):
        os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def ensure_db() -> None:
    ensure_directories()
    if not os.path.exists(DB_PATH):
        with DB_LOCK:
            with open(DB_PATH, "w", encoding="utf-8") as fh:
                json.dump(DEFAULT_DB, fh, indent=2)


def load_db() -> dict:
    ensure_db()
    with DB_LOCK:
        with open(DB_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)


def save_db(data: dict) -> None:
    ensure_db()
    with DB_LOCK:
        with open(DB_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)


def reset_db() -> None:
    save_db(deepcopy(DEFAULT_DB))
