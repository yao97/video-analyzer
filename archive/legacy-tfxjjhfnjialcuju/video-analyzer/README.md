# 🎬 视频内容分析器

> 支持音视频转录 + 画面分析 + AI 深度文案报告的一站式视频分析工具

当前版本为轻量化 Web 单页应用，前端使用原生 HTML/CSS/JS，后端基于 Flask + Whisper + Ollama / SiliconFlow。

---

## 🚀 快速开始

### 一键启动

```bash
cd video-analyzer
start_all.bat
```

自动启动两个服务：
| 服务 | 端口 | 用途 |
|------|------|------|
| 页面服务 `simple_server.py` | **8765** | 托管 `web_player_v3.html` 静态页面 |
| 转写服务 `transcribe_server.py` | **8766** | Whisper 语音转写 + AI 深度分析 API |

浏览器打开：**http://127.0.0.1:8765/web_player_v3.html**

同一局域网其他设备也可访问：**http://192.168.x.x:8765/web_player_v3.html**

### 手动启动

```powershell
# 终端 1 - 页面服务
python simple_server.py

# 终端 2 - 转写服务
python transcribe_server.py --port 8766
```

---

## ✨ 功能特性

### 1. 视频上传 & 本地预览
- 拖拽/点击上传，纯浏览器端预览（不经过后端）
- 支持 mp4 / webm 等常见格式

### 2. 画面深度分析（纯浏览器端 Canvas API）
- **逐帧颜色分析**：蓝色 / 红色 / 白色 / 肤色 / 文字像素占比统计
- **内容类型自动识别**（10 种）：知识科普、产品种草、口播、开箱、Vlog、访谈、教程、动画、风景、其他
- **视频结构拆解**：自动分镜头、帧差法检测剪辑点
- **拍摄手法分析**：运动检测、光线变化、构图评估
- **多维度图表**：颜色分布饼图、帧差异柱状图、场景热力图

### 3. 语音转写（后端 Whisper）
- OpenAI Whisper tiny 模型，中文识别
- 分片转写（10 秒/片），真实进度条
- 关键词提取 + 词云 + 高亮
- 分段时间轴、语速/情绪等衍生信息
- 支持 重新转写（一键重跑）

### 4. 🔍 AI 深度文案报告（核心亮点）
基于「叙事主权破局 + 反资本共情 + 5A 人群流转 + 实锤卖点种草 + 信任建立体系」方法论，生成 9 节结构化分析报告：

1. 内容定位与叙事主权分析
2. 反资本共情锚点拆解
3. 5A 人群流转路径推演
4. 实锤卖点与种草金句提取
5. 信任建立体系评估
6. 情绪曲线与节奏把控
7. 视觉语言与符号体系
8. 差异化竞争壁垒分析
9. 优化建议与可执行脚本

支持 **三种 AI 后端**，在页面内自由切换：

| 服务商 | 类型 | 是否需要 API Key | 模型示例 |
|--------|------|-----------------|---------|
| **Ollama** | 本地部署 | ❌ 不需要 | qwen3.5:9b、llama3.1 等 |
| **SiliconFlow** | 云端 API | ✅ 需要 | Qwen2.5-72B 等 |
| **智谱 GLM** | 云端 API | ✅ 需要 | glm-4-flash 等 |

---

## 📊 页面结构 (5 标签页)

| 标签页 | 内容 |
|--------|------|
| 📊 总览概览 | 视频信息卡片 + 内容类型识别 + 色彩分布饼图 |
| 🎞️ 视频分帧 | 缩略图网格，按时间轴排列已分析帧 |
| 📈 内容图表 | 帧差异柱状图 + 场景热力图 |
| 📝 文案结构 | 转写全文 + 时间轴 + 关键词词云 |
| 🔍 深度分析 | AI 文案报告（3 步：选服务商→验证 Key/模型→生成报告） |

---

## 🏗️ 架构

```
浏览器 (web_player_v3.html)
  │
  ├── Canvas API ──→ 逐帧颜色分析 + 内容类型识别（纯前端）
  │
  ├── HTTP POST ──→ :8766/api/transcribe      → Whisper 转写
  ├── HTTP POST ──→ :8766/api/test-api-key     → Key 验证 / Ollama 模型列表
  └── HTTP POST ──→ :8766/api/analyze-copy     → LLM 深度分析
                          │
                          ├── Ollama（本地）→ /api/chat
                          ├── SiliconFlow    → /v1/chat/completions
                          └── 智谱 GLM       → /v1/chat/completions
```

---

## 📁 项目结构

```
video-analyzer/
├── web_player_v3.html        # ★ 主页面（~1600 行，77 KB）
├── transcribe_server.py      # ★ 转写+AI 分析后端（~1500 行）
├── simple_server.py          # 静态文件服务（端口 8765）
├── start_all.bat             # 一键启动脚本
│
├── src/video_analyzer/       # FastAPI 方案（早期实验，未启用）
│   ├── services/             # 分析管道、帧分析、场景检测
│   ├── api/                  # FastAPI 路由
│   ├── schemas/              # Pydantic 数据模型
│   └── main.py               # FastAPI 入口
│
├── streamlit_app.py          # Streamlit 前端（早期实验）
├── web_player.html           # v1（全功能但布局旧）
├── web_player_v2.html        # v2（仅上传+转写，布局干净）
│
├── frames/                   # 分析过的视频帧截图
├── pyproject.toml            # Python 项目配置
└── README.md
```

> ⚠️ 根目录下的 200+ `check_*/find_*/fix_*/diag_*/debug_*` 文件均为开发调试脚本，非项目核心代码。

---

## ⚙️ 环境依赖

| 组件 | 用途 |
|------|------|
| Python 3.10+ | 后端运行 |
| Whisper (openai-whisper) | 语音转写 |
| torch (CPU) | Whisper 推理 |
| numpy / soundfile / librosa | 音频处理 |
| flask | 转写服务 Web 框架 |
| Ollama（可选） | 本地 LLM 推理 |
| requests | HTTP 客户端调用 LLM API |

安装依赖：

```powershell
pip install flask openai-whisper torch numpy soundfile librosa requests --user
```

---

## 🔧 环境变量

`.env` 文件（可选，用于云端 API 后端）：

```env
# 智谱 / 自定义 OpenAI 兼容接口
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/chat/completions

# Ollama（默认 localhost:11434）
OLLAMA_BASE=http://localhost:11434
```

> 前端页面也支持直接输入 API Key（仅本地使用，不上传任何服务器）。

---

## 📝 技术栈总结

| 类别 | 技术 |
|------|------|
| 前端 | 原生 HTML5 / CSS3 / JavaScript (ES6) |
| 图表 | Canvas API + 纯 JS 绘制（无 Chart.js 依赖） |
| 视频处理 | 浏览器端 Canvas + Video API（逐帧截图） |
| 语音识别 | OpenAI Whisper tiny (CPU 推理) |
| AI 分析 | Ollama / SiliconFlow / 智谱 (OpenAI 兼容接口) |
| 页面服务 | Python http.server (ThreadingHTTPServer) |
| API 服务 | Flask (端口 8766, 绑定 0.0.0.0) |

---

## 💡 可用模型参考

### 本地（Ollama）

```bash
# 推荐中文模型
ollama pull qwen3.5:9b      # 9B，中文能力强
ollama pull qwen3.5:4b      # 4B，更快
ollama pull llama3.1        # 8B，英文为主
```

### 云端

- SiliconFlow：https://siliconflow.cn → 个人中心 → API Key
- 智谱：https://open.bigmodel.cn → API Keys
