from datetime import datetime
from typing import Any, Dict, List

_TYPE_LABELS = {
    "text": "",
    "photo": "🖼 [Фото] ",
    "voice": "🎤 [Голосовое] ",
    "video": "🎬 [Видео] ",
    "video_note": "🎬 [Видео-кружок] ",
    "rich_message": "📰 [Статья] ",
    "unsupported": "⚠️ [Неподдерживаемый тип] ",
}


def _format_entry(entry: Dict[str, Any]) -> str:
    date = entry.get("date", "")
    sender = entry.get("sender", "Неизвестно")
    label = _TYPE_LABELS.get(entry["type"], "")

    lines = [f"### {date} — {sender}"]

    text = (entry.get("text") or "").strip()
    if "\n" in text:
        # Multi-line text (e.g. an article with headings) needs its own line —
        # a label glued onto the first line would break markdown syntax like "# ".
        lines.append(label.strip() or "*(пусто)*")
        if text:
            lines.append(text)
    else:
        body = label + text
        lines.append(body.strip() or label.strip() or "*(пусто)*")

    if entry.get("caption"):
        lines.append(f"Подпись: {entry['caption']}")

    if entry.get("media_path"):
        lines.append(f"Файл: `{entry['media_path']}`")

    return "\n".join(lines)


def build_markdown(chat_id: int, chat_title: str, entries: List[Dict[str, Any]]) -> str:
    header = [
        f"# Переписка — {chat_title}",
        f"Экспортировано: {datetime.now().isoformat(timespec='seconds')}",
        f"Сообщений: {len(entries)}",
        "",
    ]
    body = [_format_entry(e) for e in entries]
    return "\n\n".join(header + body) + "\n"
