import logging

import pytesseract
from PIL import Image

from . import config

logger = logging.getLogger(__name__)

if config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        _gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _gemini_client


def _ocr(path: str) -> str:
    try:
        image = Image.open(path)
        return pytesseract.image_to_string(image, lang=config.OCR_LANGS).strip()
    except pytesseract.TesseractNotFoundError:
        logger.warning("Tesseract OCR не установлен в системе — OCR пропущен.")
        return ""
    except Exception:
        logger.exception("OCR failed for %s", path)
        return ""


def _gemini_describe(path: str) -> str:
    if not config.GEMINI_API_KEY:
        return ""
    try:
        client = _get_gemini_client()
        image = Image.open(path)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                image,
                "Опиши, что изображено на фото, для текстового лога переписки. "
                "Если есть текст — процитируй его точно. Отвечай кратко, без вступлений, "
                "на русском.",
            ],
        )
        return (response.text or "").strip()
    except Exception:
        logger.exception("Gemini description failed for %s", path)
        return ""


def describe_image(path: str) -> str:
    """OCR first (cheap, local, great for forwarded screenshots); fall back to
    Gemini's free tier for a real scene description when OCR finds nothing."""
    ocr_text = _ocr(path)
    if len(ocr_text) >= config.OCR_MIN_CHARS:
        return f"Текст на фото (OCR): {ocr_text}"

    description = _gemini_describe(path)
    if description:
        return description

    if ocr_text:
        return f"Текст на фото (OCR): {ocr_text}"

    return "[фото: текст не распознан, описание недоступно]"
