import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
except KeyError as e:
    raise SystemExit(
        "BOT_TOKEN не задан. Скопируйте .env.example в .env и впишите токен от @BotFather."
    ) from e
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "")
OCR_LANGS = os.environ.get("OCR_LANGS", "rus+eng")
OCR_MIN_CHARS = int(os.environ.get("OCR_MIN_CHARS", "15"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

WELCOME_FILE = Path(os.environ.get("WELCOME_FILE", "./welcome.md")).resolve()
