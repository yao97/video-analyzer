"""全局配置"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 应用信息
    app_name: str = "视频内容分析器"
    debug: bool = False
    version: str = "0.1.0"

    # 上传配置
    upload_dir: Path = Path("uploads")
    max_file_size_mb: int = 500  # 最大 500MB
    allowed_extensions: set[str] = {
        "mp4", "avi", "mov", "mkv", "webm", "flv", "wmv", "m4v"
    }

    # 分析配置
    frame_sample_rate: int = 1  # 每秒采样帧数
    max_frames_to_analyze: int = 100  # 最多分析帧数
    audio_model: str = "base"  # Whisper 模型: tiny/base/small/medium/large

    # 画面分析
    enable_object_detection: bool = True
    enable_scene_recognition: bool = True
    enable_face_detection: bool = False  # 需要额外模型

    # 服务端口
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
