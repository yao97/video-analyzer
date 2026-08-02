"""
Video metadata extraction utilities.
Extracts duration, resolution, fps, and other video properties using ffprobe.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

log = get_logger("video_utils")


def get_video_metadata(video_path: str | Path) -> dict[str, Any]:
    """
    Extract video metadata using ffprobe.

    Args:
        video_path: Path to the video file.

    Returns:
        Dict with keys: duration, width, height, fps, codec, size_bytes, has_audio.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return {}

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            log.warning("ffprobe_failed", stderr=result.stderr[:200])
            return {"size_bytes": video_path.stat().st_size}

        data = json.loads(result.stdout)
        format_info = data.get("format", {})
        streams = data.get("streams", [])

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        # Parse FPS
        fps_str = video_stream.get("avg_frame_rate", "0/1")
        try:
            num, den = fps_str.split("/")
            fps = round(float(num) / float(den), 2) if float(den) != 0 else 0
        except (ValueError, ZeroDivisionError):
            fps = 0

        metadata = {
            "duration": float(format_info.get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": fps,
            "codec": video_stream.get("codec_name", "unknown"),
            "size_bytes": int(format_info.get("size", video_path.stat().st_size)),
            "has_audio": audio_stream is not None,
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "audio_channels": int(audio_stream.get("channels", 0)) if audio_stream else 0,
        }

        # Detect orientation
        if metadata["width"] > 0 and metadata["height"] > 0:
            metadata["orientation"] = "landscape" if metadata["width"] > metadata["height"] else "portrait"

        log.info("video_metadata_extracted", path=str(video_path), duration=metadata["duration"])
        return metadata

    except subprocess.TimeoutExpired:
        log.error("ffprobe_timeout", path=str(video_path))
        return {"size_bytes": video_path.stat().st_size}
    except (json.JSONDecodeError, Exception) as e:
        log.error("ffprobe_error", error=str(e), path=str(video_path))
        return {"size_bytes": video_path.stat().st_size}
