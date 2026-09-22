"""Converts Telegram's RichMessage ("article") objects into plain markdown text
for the transcript log. Not a pixel-perfect renderer — good enough to preserve
headings, lists, quotes, tables and media captions as readable text."""

from typing import List, Optional


def _text(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_text(n) for n in node)

    kind = getattr(node, "type", None)
    if kind == "custom_emoji":
        return getattr(node, "alternative_text", "") or ""
    if kind == "mathematical_expression":
        return getattr(node, "expression", "") or ""
    if kind == "anchor":
        return ""
    if kind == "button":
        button = getattr(node, "button", None)
        return _text(getattr(button, "text", None)) if button else ""
    return _text(getattr(node, "text", None))


def _caption(block) -> str:
    cap = getattr(block, "caption", None)
    if cap is None:
        return ""
    text = _text(cap.text)
    credit = getattr(cap, "credit", None)
    if credit:
        text = f"{text} — {_text(credit)}".strip(" —")
    return text


def _media_line(label: str, block) -> str:
    caption = _caption(block)
    return f"[{label}]" + (f" {caption}" if caption else "")


def _table_text(block, indent: str) -> str:
    rows = block.cells or []
    if not rows:
        return ""
    text_rows = [[_text(cell.text) if cell and cell.text else "" for cell in row] for row in rows]
    col_count = max((len(r) for r in text_rows), default=0)
    lines = []
    for i, row in enumerate(text_rows):
        padded = row + [""] * (col_count - len(row))
        lines.append(f"{indent}| " + " | ".join(c.replace("|", "\\|") for c in padded) + " |")
        if i == 0:
            lines.append(f"{indent}| " + " | ".join(["---"] * col_count) + " |")
    if getattr(block, "caption", None):
        lines.append(f"{indent}{_text(block.caption)}")
    return "\n".join(lines)


def _blocks_text(blocks: Optional[List], depth: int = 0) -> str:
    return "\n\n".join(t for t in (_block_text(b, depth) for b in blocks or []) if t)


def _block_text(block, depth: int = 0) -> str:
    if block is None:
        return ""
    indent = "  " * depth
    kind = block.type

    if kind == "paragraph":
        return indent + _text(block.text)
    if kind == "heading":
        size = max(1, min(6, block.size or 1))
        return indent + ("#" * size) + " " + _text(block.text)
    if kind == "pre":
        lang = block.language or ""
        return f"{indent}```{lang}\n{_text(block.text)}\n{indent}```"
    if kind == "footer":
        return f"{indent}_{_text(block.text)}_"
    if kind == "divider":
        return f"{indent}---"
    if kind == "mathematical_expression":
        return f"{indent}$$ {block.expression} $$"
    if kind == "anchor":
        return ""
    if kind == "list":
        lines = []
        for item in block.items:
            if item.has_checkbox:
                marker = "- [x]" if item.is_checked else "- [ ]"
            else:
                marker = item.label or "-"
            content = _blocks_text(item.blocks, depth + 1).strip()
            lines.append(f"{indent}{marker} {content}".rstrip())
        return "\n".join(lines)
    if kind == "blockquote":
        inner = _blocks_text(block.blocks, 0)
        quoted = "\n".join(f"{indent}> {l}" for l in inner.splitlines()) or f"{indent}>"
        if getattr(block, "credit", None):
            quoted += f"\n{indent}> — {_text(block.credit)}"
        return quoted
    if kind in ("pullquote", "expandable_blockquote"):
        quoted = f"{indent}> {_text(block.text)}"
        if getattr(block, "credit", None):
            quoted += f"\n{indent}> — {_text(block.credit)}"
        return quoted
    if kind in ("collage", "slideshow"):
        label = "коллаж" if kind == "collage" else "слайд-шоу"
        parts = [indent + _media_line(label, block)]
        nested = _blocks_text(block.blocks, depth)
        if nested:
            parts.append(nested)
        return "\n".join(parts)
    if kind == "table":
        return _table_text(block, indent)
    if kind == "details":
        head = f"{indent}**{_text(block.summary)}**"
        nested = _blocks_text(block.blocks, depth + 1)
        return f"{head}\n{nested}" if nested else head
    if kind == "map":
        loc = block.location
        return f"{indent}[карта: {loc.latitude}, {loc.longitude}]"
    if kind == "animation":
        return indent + _media_line("анимация", block)
    if kind == "audio":
        return indent + _media_line("аудио", block)
    if kind == "photo":
        return indent + _media_line("фото", block)
    if kind == "video":
        return indent + _media_line("видео", block)
    if kind == "voice_note":
        return indent + _media_line("голосовое", block)
    if kind == "buttons":
        labels = " | ".join(f"[{_text(b.text)}]" for b in block.buttons)
        return f"{indent}{labels}"
    if kind == "document":
        name = getattr(block.document, "file_name", None) or "файл"
        line = f"{indent}[документ: {name}]"
        caption = _caption(block)
        return f"{line} {caption}" if caption else line

    return ""


def to_markdown(rich_message) -> str:
    """Flattens a telebot.types.RichMessage into readable markdown text."""
    if rich_message is None:
        return ""
    return _blocks_text(getattr(rich_message, "blocks", None))
