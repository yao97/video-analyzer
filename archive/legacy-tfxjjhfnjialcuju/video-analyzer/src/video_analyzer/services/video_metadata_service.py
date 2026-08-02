"""
视频元数据提取服务
使用 FFmpeg 获取视频的完整元数据信息
"""
import subprocess
from pathlib import Path
from typing import Optional
from loguru import logger

from ..schemas.video_analysis import VideoMetadata


class VideoMetadataService:
    """视频元数据提取"""

    def __init__(self):
        self._ffmpeg_available: Optional[bool] = None

    def _check_ffmpeg(self) -> bool:
        """检查 FFmpeg 是否可用"""
        if self._ffmpeg_available is None:
            try:
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                self._ffmpeg_available = result.returncode == 0
            except (subprocess.SubprocessError, FileNotFoundError):
                self._ffmpeg_available = False
                logger.warning("FFmpeg 未安装，部分功能将受限")
        return self._ffmpeg_available

    def _run_ffprobe(self, video_path: str, args: list[str]) -> dict:
        """运行 ffprobe 获取信息"""
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json"] + args + [video_path]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
            )
            if result.returncode != 0:
                logger.error(f"ffprobe 失败: {result.stderr}")
                return {}
            import json
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"ffprobe 运行错误: {e}")
            return {}

    async def extract_metadata(self, video_path: str) -> VideoMetadata:
        """提取视频元数据"""
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 获取文件大小
        file_size_mb = path.stat().st_size / (1024 * 1024)

        # 使用 ffprobe 获取详细信息
        probe_data = self._run_ffprobe(
            video_path,
            ["-show_format", "-show_streams"]
        )

        # 解析视频流信息
        video_stream = None
        audio_stream = None
        
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video" and video_stream is None:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and audio_stream is None:
                audio_stream = stream

        # 提取视频信息
        if video_stream:
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            fps = self._parse_fps(video_stream.get("r_frame_rate", "0/1"))
            duration = float(probe_data.get("format", {}).get("duration", 0))
            codec = video_stream.get("codec_name", "unknown")

            # 计算总帧数
            if fps > 0 and duration > 0:
                total_frames = int(fps * duration)
            else:
                total_frames = int(video_stream.get("nb_frames", 0))
        else:
            # fallback: 使用 OpenCV
            logger.warning("FFprobe 不可用，使用 OpenCV fallback")
            width, height, fps, duration, total_frames = await self._extract_with_opencv(video_path)
            codec = "unknown (OpenCV fallback)"

        # 解析音频信息
        has_audio = audio_stream is not None
        audio_codec = audio_stream.get("codec_name") if audio_stream else None
        audio_sample_rate = int(audio_stream.get("sample_rate", 0)) if audio_stream else None
        audio_channels = int(audio_stream.get("channels", 0)) if audio_stream else None

        return VideoMetadata(
            filename=path.name,
            file_size_mb=round(file_size_mb, 2),
            duration_seconds=duration,
            width=width,
            height=height,
            fps=round(fps, 2),
            codec=codec,
            total_frames=total_frames,
            has_audio=has_audio,
            audio_codec=audio_codec,
            audio_sample_rate=audio_sample_rate,
            audio_channels=audio_channels,
        )

    def _parse_fps(self, fps_str: str) -> float:
        """解析 FPS 字符串 (e.g., '30000/1001')"""
        try:
            if "/" in fps_str:
                num, denom = fps_str.split("/")
                return float(num) / float(denom)
            return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return 0.0

    async def _extract_with_opencv(self, video_path: str) -> tuple:
        """使用 OpenCV 作为备选方案提取信息"""
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        try:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            return width, height, fps, duration, frame_count
        finally:
            cap.release()
