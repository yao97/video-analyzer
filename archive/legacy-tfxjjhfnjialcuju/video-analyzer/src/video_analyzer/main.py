"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .api.v1 import video as video_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建上传目录
    uploads = Path("uploads")
    uploads.mkdir(exist_ok=True)
    
    yield
    
    # Shutdown
    pass


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.app_name,
        description="""
        ## 视频内容分析器
        
        支持功能:
        - 🎬 **视频画面分析**: 物体检测、场景识别、颜色分析、运动检测
        - 🔊 **音频分析**: 语音识别 (Whisper)、音频特征提取
        - 📊 **智能总结**: 自动生成视频标题、描述、分类、亮点
        """,
        version=settings.version,
        lifespan=lifespan,
    )
    
    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(video_router)
    
    # 健康检查
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.version,
        }
    
    # API 文档
    @app.get("/")
    async def root():
        return {
            "message": "视频内容分析器 API",
            "docs": "/docs",
            "redoc": "/redoc",
            "endpoints": {
                "上传视频": "POST /api/v1/video/upload",
                "分析视频": "POST /api/v1/video/analyze",
                "上传并分析": "POST /api/v1/video/analyze/upload",
                "健康检查": "GET /health",
            },
        }
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "video_analyzer.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
