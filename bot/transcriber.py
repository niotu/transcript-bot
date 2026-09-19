import threading

from faster_whisper import WhisperModel

from . import config

_lock = threading.Lock()
_model = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = WhisperModel(
                    config.WHISPER_MODEL_SIZE,
                    device=config.WHISPER_DEVICE,
                    compute_type=config.WHISPER_COMPUTE_TYPE,
                )
    return _model


def transcribe(file_path: str) -> str:
    """Transcribe an audio or video file's audio track to text.

    Runs under a lock: on a 2-CPU box, concurrent transcriptions would
    just thrash each other, so requests are serialized instead.
    """
    model = _get_model()
    with _lock:
        segments, _info = model.transcribe(file_path, vad_filter=True)
        return " ".join(segment.text.strip() for segment in segments).strip()
