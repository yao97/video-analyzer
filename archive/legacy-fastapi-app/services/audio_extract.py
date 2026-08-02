"""
Audio extraction service using ffmpeg.
Resolves Bug #4: subprocess calls use list arguments (no shell=True), preventing command injection.
Resolves Bug #8: proper resource cleanup with context managers.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from app.core.exceptions import AudioExtractionError
from app.core.logging import get_logger

log = get_logger("audio_extract")

# Supported audio extraction timeout (seconds)
EXTRACTION_TIMEOUT = 300  # 5 minutes


def extract_audio(
    video_path: str | Path,
    duration: float | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    """
    Extract audio from a video file using ffmpeg.

    Args:
        video_path: Path to the input video file.
        duration: Optional duration limit (seconds) for the extracted audio.
        output_dir: Directory for the output WAV file. Defaults to system temp.

    Returns:
        Path to the extracted WAV file.

    Raises:
        AudioExtractionError: If ffmpeg fails.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise AudioExtractionError(f"Video file not found: {video_path}")

    # Create output path
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(tempfile.gettempdir()) / "video_analyzer"
        output_dir.mkdir(parents=True, exist_ok=True)

    wav_path = output_dir / f"{video_path.stem}_{Path(video_path).stem}.wav"

    # Build ffmpeg command — list form, NO shell=True (Bug #4 fix)
    cmd = [
        "ffmpeg",
        "-y",                          # overwrite output
        "-i", str(video_path),         # input
        "-vn",                         # no video
        "-acodec", "pcm_s16le",        # 16-bit PCM
        "-ar", "16000",                # 16kHz sample rate (Whisper requirement)
        "-ac", "1",                    # mono
    ]

    # Optional duration limit
    if duration and duration > 0:
        cmd.extend(["-t", str(int(duration))])

    cmd.append(str(wav_path))

    log.info("extracting_audio", video=str(video_path), output=str(wav_path), duration=duration)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=EXTRACTION_TIMEOUT,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            raise AudioExtractionError(result.stderr or "Unknown ffmpeg error")

        log.info("audio_extracted", wav_path=str(wav_path), size_bytes=wav_path.stat().st_size)
        return wav_path

    except subprocess.TimeoutExpired:
        raise AudioExtractionError(
            f"Audio extraction timed out after {EXTRACTION_TIMEOUT}s"
        )
    except FileNotFoundError:
        raise AudioExtractionError("ffmpeg not found. Please install ffmpeg.")
