"""
视频分析 API 路由
"""
import asyncio
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from ...config import settings
from ...schemas.video_analysis import (
    VideoAnalysisResponse,
    AnalysisProgress,
    VideoMetadata,
)
from ...services.analysis_pipeline import AnalysisPipeline, detailed_analyze


router = APIRouter(prefix="/api/v1/video", tags=["视频分析"])

# 全局分析管道实例
_pipeline: Optional[AnalysisPipeline] = None
_task_progress: dict[str, AnalysisProgress] = {}


def get_pipeline() -> AnalysisPipeline:
    """获取或创建分析管道"""
    global _pipeline
    if _pipeline is None:
        _pipeline = AnalysisPipeline(
            frame_sample_rate=settings.frame_sample_rate,
            max_frames=settings.max_frames_to_analyze,
            audio_model=settings.audio_model,
        )
        # 设置进度回调
        _pipeline.set_progress_callback(_on_progress)
    return _pipeline


def _on_progress(progress: AnalysisProgress):
    """进度回调"""
    _task_progress[progress.task_id] = progress


@router.post("/upload", response_model=dict)
async def upload_video(
    file: UploadFile = File(..., description="视频文件"),
) -> dict:
    """
    上传视频文件
    
    支持格式: mp4, avi, mov, mkv, webm, flv, wmv, m4v
    最大文件大小: 500MB
    """
    # 验证文件扩展名
    ext = Path(file.filename).suffix.lstrip(".").lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}。支持: {', '.join(settings.allowed_extensions)}",
        )
    
    # 验证文件大小
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成唯一文件名
    import uuid
    safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = settings.upload_dir / safe_filename
    
    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            # 分块写入以支持大文件
            chunk_size = 1024 * 1024  # 1MB
            while chunk := await file.read(chunk_size):
                buffer.write(chunk)
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            file_path.unlink()
            raise HTTPException(
                status_code=413,
                detail=f"文件过大: {file_size_mb:.1f}MB，最大支持 {settings.max_file_size_mb}MB",
            )
        
        return {
            "task_id": None,  # 尚未开始分析
            "file_path": str(file_path),
            "filename": file.filename,
            "size_mb": round(file_size_mb, 2),
            "message": "上传成功，可调用 /analyze 接口开始分析",
        }
    except HTTPException:
        raise
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/analyze", response_model=VideoAnalysisResponse)
async def analyze_video(
    video_path: str = Form(..., description="视频文件路径"),
    analyze_video: bool = Form(True, description="是否分析视频画面"),
    analyze_audio: bool = Form(True, description="是否分析音频"),
    language: str = Form("auto", description="语音识别语言"),
) -> VideoAnalysisResponse:
    """
    分析视频内容
    
    - **video_path**: 视频文件路径 (从 /upload 获取)
    - **analyze_video**: 是否分析视频画面 (物体检测、场景识别等)
    - **analyze_audio**: 是否分析音频 (语音识别、音频特征)
    - **language**: 语音识别语言 (auto/zh/en/ja/ko 等)
    """
    path = Path(video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")
    
    try:
        pipeline = get_pipeline()
        result = await pipeline.analyze(
            video_path=str(path),
            analyze_video=analyze_video,
            analyze_audio=analyze_audio,
            language=language,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/analyze/upload", response_model=VideoAnalysisResponse)
async def upload_and_analyze(
    file: UploadFile = File(..., description="视频文件"),
    analyze_video: bool = Form(True),
    analyze_audio: bool = Form(True),
    language: str = Form("auto"),
) -> VideoAnalysisResponse:
    """
    一键上传并分析视频 (便捷接口)
    
    等同于调用 /upload + /analyze
    """
    # 先上传
    upload_result = await upload_video(file)
    file_path = upload_result["file_path"]
    
    try:
        # 再分析
        pipeline = get_pipeline()
        result = await pipeline.analyze(
            video_path=file_path,
            analyze_video=analyze_video,
            analyze_audio=analyze_audio,
            language=language,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/progress/{task_id}", response_model=AnalysisProgress)
async def get_progress(task_id: str) -> AnalysisProgress:
    """获取分析任务进度"""
    progress = _task_progress.get(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return progress


@router.get("/metadata/{task_id}")
async def get_metadata(task_id: str):
    """获取已分析视频的元数据 (便捷查询)"""
    progress = _task_progress.get(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 这里可以存储分析结果后返回
    return {
        "task_id": task_id,
        "status": progress.status,
        "progress_percent": progress.progress_percent,
    }


@router.delete("/cleanup")
async def cleanup_files():
    """清理上传的文件"""
    try:
        if settings.upload_dir.exists():
            for file in settings.upload_dir.glob("*"):
                if file.is_file():
                    file.unlink()
        return {"message": "清理完成", "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")
