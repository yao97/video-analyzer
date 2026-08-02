"""视频分析相关的数据模型"""
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    """视频元数据"""
    filename: str
    file_size_mb: float
    duration_seconds: float
    width: int
    height: int
    fps: float
    codec: str
    total_frames: int
    has_audio: bool
    audio_codec: Optional[str] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None


class DetectedObject(BaseModel):
    """检测到的物体"""
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2


class SceneInfo(BaseModel):
    """场景信息"""
    scene_id: int
    start_time: float
    end_time: float
    description: str
    tags: list[str]
    key_frame_index: int


class FrameAnalysis(BaseModel):
    """单帧分析结果"""
    frame_index: int
    timestamp: float
    scene_description: str
    detected_objects: list[DetectedObject]
    dominant_colors: list[str]
    motion_intensity: float = Field(ge=0.0, le=1.0)


class AudioSegment(BaseModel):
    """音频片段"""
    start_time: float
    end_time: float
    text: str
    language: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class AudioAnalysis(BaseModel):
    """音频分析结果"""
    transcript: str
    language: Optional[str] = None
    language_confidence: float
    segments: list[AudioSegment]
    duration_seconds: float
    has_speech: bool
    speech_ratio: float = Field(ge=0.0, le=1.0)  # 语音占比
    energy_level: float = Field(ge=0.0, le=1.0)  # 音频能量


class VideoSummary(BaseModel):
    """视频总结"""
    title: str
    description: str
    categories: list[str]
    key_topics: list[str]
    highlights: list[str]
    sentiment: str  # positive/negative/neutral
    target_audience: Optional[str] = None
    content_warnings: list[str] = []


class VideoAnalysisRequest(BaseModel):
    """分析请求"""
    video_path: str
    analyze_video: bool = True
    analyze_audio: bool = True
    extract_frames: bool = False
    max_frames: int = 100
    language: str = "auto"  # auto, zh, en, etc.


class AnalysisProgress(BaseModel):
    """分析进度"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress_percent: float = Field(ge=0.0, le=100.0)
    current_step: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class VideoAnalysisResponse(BaseModel):
    """完整分析结果"""
    task_id: str
    video_path: str
    metadata: VideoMetadata
    frame_analyses: list[FrameAnalysis]
    audio_analysis: Optional[AudioAnalysis]
    scenes: list[SceneInfo]
    summary: VideoSummary
    analyzed_at: datetime = Field(default_factory=datetime.now)
    processing_time_seconds: float
