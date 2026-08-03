# Video Content Analyzer (VCA)

短视频竞品反向拆解工具 — 上传视频 → Qwen3-ASR 语音转写 → LLM 深度分析 → 九节结构化报告（含分镜头表、文案拆解、爆款文案库）。

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
├── Dockerfile                 # Docker 镜像（Flask + ffmpeg）
├── docker-compose.yml         # 单体 API + 可选 Ollama
├── .dockerignore
├── .env.example               # 部署环境变量
├── docs/                      # 文档
└── archive/                   # 旧版参考（已归档）
```

## 语音识别引擎（Qwen3-ASR-1.7B）

上传视频后**先提取音频，不自动转写**；音频就绪后点击「开始转写」由 **Qwen3-ASR-1.7B 本地大模型**识别，输出带字级时间戳的分段（ForceAligner 对齐）。

- 硬件：GPU（DirectML + Vulkan）或 CPU；RTX 3050 上 52s 音频约 4 秒转写（RTF 0.077）
- 识别准确度可调：环境变量 `QWEN3_ASR_CONTEXT`（热词提示，默认含直播带货领域词）/ `QWEN3_ASR_TEMPERATURE`（采样温度，默认 0.3，越低越保守）

### Qwen3-ASR-1.7B 部署

1. 安装依赖：`pip install onnxruntime-directml pydub scipy gguf srt`
2. 克隆引擎：`git clone https://github.com/HaujetZhao/Qwen3-ASR-GGUF.git backend/qwen3_asr_gguf_src`
3. 下载模型（Model Release，解压到 `backend/qwen3_asr_models/`）：
   - `Qwen3-ASR-1.7B-gguf.zip`（1.3GB）
   - `Qwen3-ForceAligner-0.6B-gguf.zip`（481MB，时间戳必需）
4. 下载 llama.cpp Windows Vulkan 二进制，解压 DLL 到 `backend/qwen3_asr_gguf_src/qwen_asr_gguf/inference/bin/`
   - ⚠️ 用 **b8996** 版本（最新版 b10229+ 与引擎不兼容，会 access violation）
5. 重启服务即可（引擎默认固定 Qwen3-ASR）

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
# 编辑 .env：填 LLM_API_KEY、选 LLM_PROVIDER、QWEN3_ASR_CONTEXT 等
```

### 2. 构建并启动（仅 API）

```bash
docker compose up -d --build
```

- 访问 `http://<服务器IP>:8766/`
- 语音识别引擎为 Qwen3-ASR-1.7B（模型文件需手动放入 `backend/qwen3_asr_models/`，见上文部署章节）

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

- **一次只转写一个视频**：Qwen3-ASR 引擎实例较重，已强制串行（排队等待）
- Qwen3-ASR 推理约需 2-3GB 内存（GPU 显存 ~1.6GB + 系统内存），Docker 默认限 4g
- 深度分析九节报告生成较长（含大量表格），Ollama 已配置 `num_predict=8192` 防截断

## 文档

- [项目功能介绍](docs/项目功能介绍.md)
- [项目优化建议](docs/项目优化建议.md)
- [后端系统介绍手册](docs/后端系统介绍手册.md)
