"""
Whisper transcription service.
Supports GPU (CUDA) device selection (Bug #13 fix) and progress tracking.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.exceptions import TranscriptionError
from app.core.logging import get_logger
from app.config import get_settings

log = get_logger("transcription")

# Whisper model cache (avoid reloading on every call)
_whisper_model = None
_whisper_model_name = ""


def _load_whisper_model():
    """Load Whisper model with GPU support (Bug #13 fix)."""
    global _whisper_model, _whisper_model_name

    if _whisper_model is not None:
        return _whisper_model

    settings = get_settings()

    try:
        import torch
        import whisper
    except ImportError as e:
        raise TranscriptionError(f"Whisper or torch not installed: {e}")

    # Auto-detect GPU (Bug #13 fix)
    device = settings.whisper_device
    if device == "cpu":
        # Double-check: if CUDA is available but device is set to cpu,
        # still respect the setting (user may want CPU mode)
        pass
    else:
        try:
            import torch
            if not torch.cuda.is_available():
                log.warning("cuda_requested_but_unavailable", msg="Falling back to CPU")
                device = "cpu"
        except ImportError:
            device = "cpu"

    model_name = settings.whisper_model
    log.info("loading_whisper_model", model=model_name, device=device)

    try:
        _whisper_model = whisper.load_model(model_name, device=device)
        _whisper_model_name = model_name
        log.info("whisper_model_loaded", model=model_name, device=device)
        return _whisper_model
    except Exception as e:
        raise TranscriptionError(f"Failed to load Whisper model '{model_name}': {e}")


def get_model_info() -> dict[str, str]:
    """Get current Whisper model info for health check."""
    settings = get_settings()
    return {
        "model": settings.whisper_model,
        "device": settings.whisper_device,
    }


def transcribe_audio(
    audio_path: str | Path,
    language: str | None = None,
    progress_callback: Any | None = None,
) -> dict:
    """
    Transcribe an audio file using Whisper.

    Args:
        audio_path: Path to the WAV audio file.
        language: Optional language hint (e.g., 'zh', 'en').
        progress_callback: Optional callback for progress updates.

    Returns:
        Dict with keys: text, segments, language, duration.

    Raises:
        TranscriptionError: If transcription fails.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    model = _load_whisper_model()

    log.info("starting_transcription", audio=str(audio_path), language=language)

    try:
        # Whisper transcribe options
        transcribe_opts = {
            "verbose": False,  # Suppress stdout
        }
        if language:
            transcribe_opts["language"] = language

        result = model.transcribe(str(audio_path), **transcribe_opts)

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg.get("start", 0), 2),
                "end": round(seg.get("end", 0), 2),
                "text": seg.get("text", "").strip(),
            })

        full_text = result.get("text", "").strip()
        detected_language = result.get("language", "unknown")

        # Extract keywords from the transcript
        from app.utils.text import extract_keywords
        keywords = extract_keywords(full_text)

        log.info(
            "transcription_complete",
            language=detected_language,
            segment_count=len(segments),
            text_length=len(full_text),
        )

        if progress_callback:
            progress_callback(1.0, "Transcription complete")

        return {
            "text": full_text,
            "segments": segments,
            "language": detected_language,
            "keywords": keywords,
        }

    except Exception as e:
        log.error("transcription_failed", error=str(e), audio=str(audio_path))
        raise TranscriptionError(str(e))


def cleanup():
    """Release Whisper model from memory."""
    global _whisper_model, _whisper_model_name
    _whisper_model = None
    _whisper_model_name = ""
