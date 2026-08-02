# Video Content Analyzer (VCA)

短视频竞品反向拆解工具 — 上传视频 → Whisper 转写 → LLM 深度分析 → 九节结构化报告（含分镜头表、文案拆解、爆款文案库）。

## 架构

**单体 Flask 服务**：`backend/transcribe_server.py` 一个进程同时提供转写/分析 API 和前端静态页。

```
.
├── backend/
│   ├── transcribe_server.py   # 单体 Flask 服务（转写 + 深度分析 + serve 前端）
│   ├── requirements.txt       # 实际运行依赖
│   └── .env.example           # 环境变量模板
├── frontend/
│   ├── web_player.html        # 前端唯一真相源（服务直接 serve 此文件）
│   └── chart.umd.min.js       # 图表库
├── Dockerfile                 # Docker 镜像（Flask + Whisper + ffmpeg）
├── docker-compose.yml         # 单体 API + 可选 Ollama
├── .dockerignore
├── .env.example               # 部署环境变量
├── docs/                      # 文档
└── archive/                   # 旧版参考（已归档）
```

## 本地运行（不装 Docker）

```bash
# 1. 安装依赖（建议虚拟环境）
pip install -r backend/requirements.txt

# 2. 启动（需要本机已装 ffmpeg）
cd backend
python transcribe_server.py --host 0.0.0.0 --port 8766 --model small
```

- 访问 `http://<本机IP>:8766/` 即前端页面
- 临时文件（音频/视频/WAV）写入系统 temp 目录，不污染仓库

## Docker 部署

> 本地开发环境不需要 Docker；以下步骤在有 Docker 的服务器/机器上执行。

### 1. 准备环境变量

```bash
cp .env.example .env
# 编辑 .env：填 LLM_API_KEY、选 LLM_PROVIDER、WHISPER_MODEL 等
```

### 2. 构建并启动（仅 API）

```bash
docker compose up -d --build
```

- 访问 `http://<服务器IP>:8766/`
- Whisper 模型首次运行自动下载，缓存在 `whisper-models` 卷，重启不重复下载
- 默认 `WHISPER_MODEL=small`（约 460MB），内存紧张改 `tiny`

### 3. 启用 Ollama 本地 LLM（可选）

```bash
docker compose --profile llm up -d --build
# .env 里设置 OLLAMA_BASE=http://ollama:11434
# 之后在容器内拉取模型：docker compose exec ollama ollama pull qwen3.5:9b
```

### 4. 使用宿主机已装的 Ollama（推荐，省资源）

```bash
# .env 里设置 OLLAMA_BASE=http://host.docker.internal:11434
docker compose up -d --build
```

### 5. 运维

```bash
docker compose logs -f api      # 查看日志
docker compose restart api      # 重启
docker compose down             # 停止（保留数据卷）
docker compose down -v          # 停止并清空数据（模型需重新下载）
```

## 深度分析 LLM 提供商

| Provider | 配置 | 说明 |
|----------|------|------|
| siliconflow | `LLM_PROVIDER=siliconflow` + `LLM_API_KEY` | 硅基流动，默认推荐 |
| deepseek | `LLM_PROVIDER=deepseek` + `LLM_API_KEY` | DeepSeek 官方 API |
| zhipu | `LLM_PROVIDER=zhipu` + `LLM_API_KEY` | 智谱 GLM |
| ollama | `LLM_PROVIDER=ollama`（无需 Key） | 本地推理，需 `OLLAMA_BASE` |

## 已知问题与注意事项

- **一次只转写一个视频**：并发上传多个视频可能触发 Whisper 模型实例加载竞争导致进程卡死（已定位，建议串行使用）
- Whisper `small` 模型推理约需 1.5-2GB 内存，Docker 默认限 4g
- 深度分析九节报告生成较长（含大量表格），Ollama 已配置 `num_predict=8192` 防截断

## 文档

- [项目功能介绍](docs/项目功能介绍.md)
- [项目优化建议](docs/项目优化建议.md)
- [后端系统介绍手册](docs/后端系统介绍手册.md)
