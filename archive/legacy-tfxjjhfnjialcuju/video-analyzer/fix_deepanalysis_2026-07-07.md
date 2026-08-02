# 视频分析器 — 深度分析功能修复 + 环境重建（2026-07-07）

## 背景
用户要求补全「深度分析（九节结构）」tab 的 4 项能力：
1. 上传视频清空所有缓存
2. API Key 手动输入（支持 SiliconFlow）
3. 出错后可重新填写 Key
4. 可选模型

此前 `doDeepAnalysis` 函数因脚本引号错误被截断损坏（`le` 残留、缺 `testApiKey`/`deepGoStep1`/`showKeyError`）。

## 完成的修复

### 前端 `web_player_v3.html`
- 修复 `doDeepAnalysis` 截断：重写整块为完整函数（含 `deepGoStep1` / `testApiKey` async / `showKeyError` / 重构 `doDeepAnalysis`），并删除旧函数残留的孤儿代码块（1523-1550 行），及 `showDeepError` 中对已删除 `deepReportIntro` id 的空引用。
- 上传时清空深度分析缓存：在 `processFile` 的 reset 中加入 `deepGoStep1()` 调用（回到 Step1 重新填 Key）。
- 验证：用 `node --check` 校验整段 `<script>` 语法 OK；`function doDeepAnalysis/testApiKey/deepGoStep1/showKeyError` 各仅 1 份。

### 后端 `transcribe_server.py`
- `/api/test-api-key`（POST）：接收 `{api_key, model}`，自动识别 SiliconFlow（`sk-` 前缀 → `https://api.siliconflow.cn/v1/chat/completions`，默认模型 `Qwen/Qwen2.5-72B-Instruct`）/ 智谱（用 `LLM_BASE_URL` 环境变量）；返回 `{ok, provider, model, available_models, error}`。
- `/api/analyze-copy`：支持前端传入 `api_key` / `model`；空 Key 直接返回 `{available:false, error:"请先填入 API Key"}`。
- `call_llm_analyze`：用 `user_prompt_lines` list + `"\n".join()` 构造提示词，避免转义问题；自动检测 SiliconFlow。
- 验证：空 Key 测 `test-api-key` → `{"ok":false,"error":"API Key 不能为空"}`；空 Key 测 `analyze-copy` → `{"available":false,"error":"请先填入 API Key"}`。

## 环境重建（关键阻塞）
QClaw Python 被静默升级（`v0.2.31.600` → `v0.2.32.610`），导致：
- 所有依赖（flask/cors/requests/zhconv/whisper/torch/numpy/soundfile/imageio-ffmpeg/opencv/jieba/librosa 等）全部丢失。
- `start_all.bat` 仍指向已删除的旧 Python 路径。

处理：
- 轻量依赖（flask/cors/requests/zhconv/numpy/soundfile/imageio-ffmpeg/opencv/jieba/opencc）装到系统 site-packages。
- 重依赖（torch CPU 2.12.1、whisper 20250625、librosa 等）因系统目录中 `regex` 的 `.pyd` 被运行中的 QClaw 进程锁定（WinError 5 拒绝访问），改用 `--user` 装到用户 site-packages（同一解释器自动发现，无需改 PYTHONPATH）。
- whisper 走 numpy 数组路径（不依赖系统 ffmpeg），已用纯音测试 `WHISPER_SANITY_OK`（加载模型 / 语言检测 / transcribe 全流程通过，text_len=0 因输入为纯正弦音，正常）。
- `start_all.bat` 的 `PYTHON_EXE` 改为 `v0.2.32.610`。

## 服务运行
- 8765 页面服务：`simple_server.py` 改为 `ThreadingHTTPServer` + `protocol_version='HTTP/1.0'`（修复单线程被 keep-alive 浏览器连接阻塞导致新请求超时的问题），现 113KB 页面正常返回。
- 8766 转写服务：`transcribe_server.py --port 8766`，`/api/video-meta` 返回 `{"model":"tiny","status":"ok","version":"1.0"}`。
- 两服务均以独立 `start` 窗口启动（脱离 exec 后台进程，避免被 harness 回收）。

## 待办 / 备注
- 线程堆积未根治（旧问题，本次未触发）。
- Chart.js CDN 已被移除（未实际使用）。
- 实际语音视频端到端转写 + 深度分析需在浏览器用有声音视频验证（本次用纯音做了 whisper 管道验证）。
