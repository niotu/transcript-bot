import json
import threading
from pathlib import Path
from typing import Any, Dict, List

from . import config

_lock = threading.RLock()


def _chat_dir(chat_id: int) -> Path:
    d = config.DATA_DIR / str(chat_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def media_dir(chat_id: int) -> Path:
    d = _chat_dir(chat_id) / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _session_file(chat_id: int) -> Path:
    return _chat_dir(chat_id) / "session.json"


def get_entries(chat_id: int) -> List[Dict[str, Any]]:
    path = _session_file(chat_id)
    if not path.exists():
        return []
    with _lock:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def add_entry(chat_id: int, entry: Dict[str, Any]) -> None:
    with _lock:
        entries = get_entries(chat_id)
        entries.append(entry)
        with open(_session_file(chat_id), "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)


def clear(chat_id: int) -> None:
    with _lock:
        path = _session_file(chat_id)
        if path.exists():
            path.unlink()
        for f in media_dir(chat_id).iterdir():
            if f.is_file():
                f.unlink()
