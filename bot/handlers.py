import logging
import traceback
import uuid
from datetime import datetime
from typing import Optional, Tuple

import telebot
from telebot import types

from . import config, md_export, session_store, transcriber, vision

logger = logging.getLogger(__name__)

MAX_TELEGRAM_FILE_SIZE = 20 * 1024 * 1024  # Bot API download limit


def _welcome_text() -> str:
    try:
        return config.WELCOME_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.warning("Welcome file not found: %s", config.WELCOME_FILE)
        return "Пересылайте сюда сообщения переписки, затем отправьте /export."


def _commands_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("/export", "/status")
    kb.row("/clear", "/help")
    return kb


def _display_name(user: Optional[types.User]) -> str:
    if user is None:
        return "Неизвестно"
    name = " ".join(p for p in [user.first_name, user.last_name] if p)
    if user.username:
        name = f"{name} (@{user.username})" if name else f"@{user.username}"
    return name or "Неизвестно"


def _sender_and_date(message: types.Message) -> Tuple[str, str]:
    origin = message.forward_origin
    if origin is not None:
        date = datetime.fromtimestamp(origin.date).strftime("%Y-%m-%d %H:%M")
        if isinstance(origin, types.MessageOriginUser):
            return _display_name(origin.sender_user), date
        if isinstance(origin, types.MessageOriginHiddenUser):
            return origin.sender_user_name, date
        if isinstance(origin, types.MessageOriginChat):
            name = origin.sender_chat.title or "Чат"
            if origin.author_signature:
                name = f"{name} ({origin.author_signature})"
            return name, date
        if isinstance(origin, types.MessageOriginChannel):
            name = origin.chat.title or "Канал"
            if origin.author_signature:
                name = f"{name} ({origin.author_signature})"
            return name, date

    date = datetime.fromtimestamp(message.date).strftime("%Y-%m-%d %H:%M")
    return _display_name(message.from_user), date


def _save_media(bot: telebot.TeleBot, chat_id: int, file_id: str, ext: str) -> str:
    tg_file = bot.get_file(file_id)
    content = bot.download_file(tg_file.file_path)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = session_store.media_dir(chat_id) / filename
    path.write_bytes(content)
    return str(path)


def register(bot: telebot.TeleBot) -> None:
    @bot.message_handler(commands=["start", "help"])
    def cmd_start(message: types.Message):
        bot.reply_to(
            message,
            _welcome_text(),
            reply_markup=_commands_keyboard(),
            parse_mode="Markdown",
        )

    @bot.message_handler(commands=["status"])
    def cmd_status(message: types.Message):
        count = len(session_store.get_entries(message.chat.id))
        bot.reply_to(message, f"Накоплено сообщений: {count}", reply_markup=_commands_keyboard())

    @bot.message_handler(commands=["clear"])
    def cmd_clear(message: types.Message):
        session_store.clear(message.chat.id)
        bot.reply_to(message, "Накопленные сообщения очищены.", reply_markup=_commands_keyboard())

    @bot.message_handler(commands=["export"])
    def cmd_export(message: types.Message):
        chat_id = message.chat.id
        entries = session_store.get_entries(chat_id)
        if not entries:
            bot.reply_to(
                message,
                "Пока нечего экспортировать — перешлите сообщения.",
                reply_markup=_commands_keyboard(),
            )
            return

        status = bot.reply_to(message, "Собираю .md файл...", reply_markup=_commands_keyboard())
        md_text = md_export.build_markdown(chat_id, str(chat_id), entries)
        out_path = session_store.media_dir(chat_id).parent / f"transcript_{uuid.uuid4().hex[:8]}.md"
        out_path.write_text(md_text, encoding="utf-8")

        with open(out_path, "rb") as f:
            bot.send_document(chat_id, f, visible_file_name="transcript.md")
        out_path.unlink()
        bot.edit_message_text("Готово.", chat_id, status.message_id)
        session_store.clear(chat_id)

    @bot.message_handler(content_types=["text"])
    def handle_text(message: types.Message):
        if message.text.startswith("/"):
            return
        sender, date = _sender_and_date(message)
        session_store.add_entry(
            message.chat.id,
            {"type": "text", "sender": sender, "date": date, "text": message.text},
        )

    @bot.message_handler(content_types=["photo"])
    def handle_photo(message: types.Message):
        sender, date = _sender_and_date(message)
        chat_id = message.chat.id
        try:
            largest = message.photo[-1]
            path = _save_media(bot, chat_id, largest.file_id, ".jpg")
            description = vision.describe_image(path)
        except Exception:
            logger.error("Photo processing failed:\n%s", traceback.format_exc())
            path, description = None, "[не удалось обработать фото]"

        session_store.add_entry(
            chat_id,
            {
                "type": "photo",
                "sender": sender,
                "date": date,
                "text": description,
                "caption": message.caption,
                "media_path": path,
            },
        )

    def _handle_audio_like(
        message: types.Message, kind: str, file_id: str, ext: str, file_size: Optional[int]
    ):
        sender, date = _sender_and_date(message)
        chat_id = message.chat.id
        if file_size and file_size > MAX_TELEGRAM_FILE_SIZE:
            path, text = None, "[файл больше 20 МБ, Bot API не позволяет его скачать]"
        else:
            try:
                path = _save_media(bot, chat_id, file_id, ext)
                text = transcriber.transcribe(path)
            except Exception:
                logger.error("%s processing failed:\n%s", kind, traceback.format_exc())
                path, text = None, "[не удалось распознать аудио]"

        session_store.add_entry(
            chat_id,
            {
                "type": kind,
                "sender": sender,
                "date": date,
                "text": text,
                "caption": getattr(message, "caption", None),
                "media_path": path,
            },
        )

    @bot.message_handler(content_types=["voice"])
    def handle_voice(message: types.Message):
        _handle_audio_like(
            message, "voice", message.voice.file_id, ".ogg", message.voice.file_size
        )

    @bot.message_handler(content_types=["video"])
    def handle_video(message: types.Message):
        _handle_audio_like(
            message, "video", message.video.file_id, ".mp4", message.video.file_size
        )

    @bot.message_handler(content_types=["video_note"])
    def handle_video_note(message: types.Message):
        _handle_audio_like(
            message,
            "video_note",
            message.video_note.file_id,
            ".mp4",
            message.video_note.file_size,
        )

    @bot.message_handler(content_types=["audio"])
    def handle_audio(message: types.Message):
        _handle_audio_like(
            message, "voice", message.audio.file_id, ".mp3", message.audio.file_size
        )

    @bot.message_handler(
        content_types=["document", "sticker", "animation", "location", "contact", "poll"]
    )
    def handle_unsupported(message: types.Message):
        sender, date = _sender_and_date(message)
        label = message.content_type
        if message.content_type == "document" and message.document.file_name:
            label = f"document: {message.document.file_name}"
        session_store.add_entry(
            message.chat.id,
            {"type": "unsupported", "sender": sender, "date": date, "text": label},
        )
