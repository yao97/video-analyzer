"""
分析管道 - 核心编排器
整合所有分析服务,统一执行视频分析流程
"""
import asyncio
import cv2
import time
import uuid
from pathlib import Path
from typing import Optional, Callable
from loguru import logger

from ..config import settings
from ..schemas.video_analysis import (
    VideoAnalysisResponse,
    VideoMetadata,
    FrameAnalysis,
    AudioAnalysis,
    SceneInfo,
    VideoSummary,
    AnalysisProgress,
)
from .video_metadata_service import VideoMetadataService
from .frame_analyzer import FrameAnalyzer
from .audio_analyzer import AudioAnalyzer
from .scene_detector import SceneDetector
from .video_summary_service import VideoSummaryService


class AnalysisPipeline:
    """
    视频分析管道
    
    执行流程:
    1. 提取视频元数据
    2. 采样分析帧
    3. 检测场景切换
    4. 音频分析 (语音识别)
    5. 生成总结报告
    """

    def __init__(
        self,
        frame_sample_rate: int = 1,
        max_frames: int = 100,
        audio_model: str = "base",
    ):
        self._frame_sample_rate = frame_sample_rate
        self._max_frames = max_frames
        self._audio_model = audio_model
        
        # 初始化各服务
        self._metadata_service = VideoMetadataService()
        self._frame_analyzer = FrameAnalyzer()
        self._audio_analyzer = AudioAnalyzer(model_size=audio_model)
        self._scene_detector = SceneDetector()
        self._summary_service = VideoSummaryService()
        
        # 进度回调
        self._progress_callback: Optional[Callable[[AnalysisProgress], None]] = None
        
        # 任务状态
        self._tasks: dict[str, AnalysisProgress] = {}

    def set_progress_callback(
        self,
        callback: Callable[[AnalysisProgress], None],
    ):
        """设置进度回调"""
        self._progress_callback = callback

    def _update_progress(
        self,
        task_id: str,
        status: str,
        progress_percent: float,
        current_step: str,
    ):
        """更新任务进度"""
        task = self._tasks.get(task_id)
        if task:
            task.status = status
            task.progress_percent = progress_percent
            task.current_step = current_step
            
            if status == "processing":
                task.started_at = task.started_at or time.time()
            elif status in ("completed", "failed"):
                task.completed_at = time.time()
        
        if self._progress_callback:
            self._progress_callback(task)

    async def analyze(
        self,
        video_path: str,
        analyze_video: bool = True,
        analyze_audio: bool = True,
        language: str = "auto",
    ) -> VideoAnalysisResponse:
        """
        执行完整视频分析
        
        Args:
            video_path: 视频文件路径
            analyze_video: 是否分析视频画面
            analyze_audio: 是否分析音频
            language: 语音识别语言 (auto/zh/en 等)
            
        Returns:
            完整的分析结果
        """
        # 生成任务 ID
        task_id = str(uuid.uuid4())[:8]
        self._tasks[task_id] = AnalysisProgress(
            task_id=task_id,
            status="processing",
            progress_percent=0.0,
            current_step="初始化",
        )
        
        start_time = time.time()
        
        try:
            # ========== Step 1: 提取元数据 ==========
            self._update_progress(task_id, "processing", 5.0, "提取视频元数据")
            metadata = await self._metadata_service.extract_metadata(video_path)
            logger.info(f"[{task_id}] 元数据提取完成: {metadata.duration_seconds}s")
            
            # ========== Step 2: 采样分析帧 ==========
            frame_analyses: list[FrameAnalysis] = []
            if analyze_video:
                self._update_progress(task_id, "processing", 15.0, "采样分析视频帧")
                frame_analyses = await self._sample_and_analyze_frames(
                    video_path,
                    metadata,
                    task_id,
                )
            
            # ========== Step 3: 场景检测 ==========
            scenes: list[SceneInfo] = []
            if analyze_video:
                self._update_progress(
                    task_id, "processing", 50.0, "检测场景切换"
                )
                scenes = await self._scene_detector.detect_scenes_async(
                    video_path,
                    fps=metadata.fps,
                )
                logger.info(f"[{task_id}] 检测到 {len(scenes)} 个场景")
            
            # ========== Step 4: 音频分析 ==========
            audio_analysis: Optional[AudioAnalysis] = None
            if analyze_audio and metadata.has_audio:
                self._update_progress(task_id, "processing", 65.0, "分析音频内容")
                audio_analysis = await self._audio_analyzer.analyze_audio(
                    video_path,
                    language=language,
                )
                logger.info(
                    f"[{task_id}] 音频分析完成, "
                    f"转录 {len(audio_analysis.segments)} 段"
                )
            
            # ========== Step 5: 生成总结 ==========
            self._update_progress(task_id, "processing", 90.0, "生成总结报告")
            summary = await self._summary_service.generate_summary(
                metadata=metadata,
                frame_analyses=frame_analyses,
                audio_analysis=audio_analysis,
                scenes=scenes,
            )
            
            # 计算总耗时
            processing_time = time.time() - start_time
            
            # 标记完成
            self._update_progress(task_id, "completed", 100.0, "分析完成")
            
            return VideoAnalysisResponse(
                task_id=task_id,
                video_path=video_path,
                metadata=metadata,
                frame_analyses=frame_analyses,
                audio_analysis=audio_analysis,
                scenes=scenes,
                summary=summary,
                processing_time_seconds=round(processing_time, 2),
            )
            
        except Exception as e:
            logger.exception(f"[{task_id}] 分析失败: {e}")
            self._update_progress(
                task_id, "failed", 0.0, f"错误: {str(e)[:50]}"
            )
            raise

    async def _sample_and_analyze_frames(
        self,
        video_path: str,
        metadata: VideoMetadata,
        task_id: str,
    ) -> list[FrameAnalysis]:
        """采样并分析帧"""
        # 计算采样间隔
        total_frames = metadata.total_frames
        sample_interval = max(
            1,
            total_frames // min(self._max_frames, total_frames)
        )
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频: {video_path}")
        
        frame_analyses = []
        frame_idx = 0
        analyzed = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 按间隔采样
                if frame_idx % sample_interval == 0:
                    timestamp = frame_idx / metadata.fps
                    
                    # 分析当前帧
                    analysis = await self._frame_analyzer.analyze_frame(
                        frame=frame,
                        frame_index=frame_idx,
                        timestamp=timestamp,
                    )
                    frame_analyses.append(analysis)
                    analyzed += 1
                    
                    # 更新进度 (15% -> 50%)
                    base_progress = 15.0
                    progress_range = 35.0
                    current_progress = base_progress + (
                        (analyzed / min(self._max_frames, total_frames // sample_interval))
                        * progress_range
                    )
                    self._update_progress(
                        task_id, "processing", current_progress,
                        f"分析帧 {analyzed}/{min(self._max_frames, total_frames // sample_interval)}"
                    )
                    
                    # 限制最大帧数
                    if analyzed >= self._max_frames:
                        break
                
                frame_idx += 1
        finally:
            cap.release()
        
        logger.info(f"[{task_id}] 帧分析完成,分析了 {len(frame_analyses)} 帧")
        return frame_analyses

    def get_task_progress(self, task_id: str) -> Optional[AnalysisProgress]:
        """获取任务进度"""
        return self._tasks.get(task_id)


# ========== 便捷函数 ==========

async def quick_analyze(video_path: str) -> VideoAnalysisResponse:
    """快速分析 (使用默认配置)"""
    pipeline = AnalysisPipeline()
    return await pipeline.analyze(video_path)


async def detailed_analyze(
    video_path: str,
    language: str = "auto",
    max_frames: int = 100,
) -> VideoAnalysisResponse:
    """详细分析"""
    pipeline = AnalysisPipeline(
        max_frames=max_frames,
        frame_sample_rate=1,
        audio_model="base",
    )
    return await pipeline.analyze(
        video_path,
        analyze_video=True,
        analyze_audio=True,
        language=language,
    )
