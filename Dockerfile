# ─────────────────────────────────────────────────────────────
# Video Content Analyzer - 单体 Flask + Whisper 后端
# 架构：backend/transcribe_server.py (Flask 8766) + frontend/ (静态页)
# 注意：本地开发环境不装 Docker 也没关系，本文件供有 Docker 的机器构建
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── 系统依赖：ffmpeg（音频提取）+ curl（健康检查） ──
# Whisper 音频解码需要 ffmpeg，imageio-ffmpeg 自带二进制但显式安装更稳
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── 先复制依赖清单再安装（利用 Docker 层缓存） ──
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── 复制应用代码 ──
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# ── 非 root 运行（安全） ──
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/.cache/whisper /app/exports /app/tmp \
    && chown -R appuser:appuser /app
USER appuser

# ── 环境变量（可被 compose 覆盖） ──
ENV WHISPER_MODEL=small \
    OLLAMA_BASE=http://host.docker.internal:11434 \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=8766 \
    HF_HOME=/app/.cache/huggingface

# ── 暴露端口 ──
EXPOSE 8766

# ── 健康检查：Flask 根路径返回页面即健康 ──
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8766/ || exit 1

# ── 启动 ──
CMD ["python", "-B", "backend/transcribe_server.py", "--host", "0.0.0.0", "--port", "8766", "--model", "small"]
