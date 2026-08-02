"""

Video Content Analyzer - Python Backend

功能：音频提取 + Whisper 语音转写（分片真实进度，无需系统 ffmpeg）

依赖：whisper / imageio-ffmpeg / flask / soundfile / numpy

启动：python transcribe_server.py

接口：POST /api/transcribe        上传视频，开始转写

      GET  /api/status/<job_id>  查询任务状态（含真实进度）

      GET  /api/result/<job_id>  获取转写结果

      GET  /api/video-meta       视频元数据

"""

import os

import uuid

import json

import threading

import subprocess

import tempfile

import time

from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from flask_cors import CORS

import zhconv  # 繁体→简体转换



# ── 懒加载 ──

_whisper_model = None
_whisper_model_name = "tiny"  # overridden by --model arg at startup
_ffmpeg_exe = None



def get_ffmpeg():

    """获取 imageio-ffmpeg 自带的 ffmpeg 路径（用于音频提取，不用于 Whisper）"""

    global _ffmpeg_exe

    if _ffmpeg_exe is None:

        try:

            import imageio_ffmpeg

            _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

            print(f"[FFmpeg] 使用 imageio-ffmpeg: {_ffmpeg_exe}")

        except ImportError:

            _ffmpeg_exe = "ffmpeg"

    return _ffmpeg_exe



def get_whisper_model():

    """懒加载 Whisper 模型"""

    global _whisper_model, _whisper_model_name

    if _whisper_model is None:

        import whisper

        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

        print(f"[Whisper] 加载 {_whisper_model_name} 模型 (device={device})...")

        _whisper_model = whisper.load_model(_whisper_model_name, device=device)

        print(f"[Whisper] 模型加载完成 (device={device})")

    return _whisper_model



def mask_key(key: str) -> str:
    """脱敏显示 API Key，避免完整 Key 出现在日志/打印中（#5）。"""
    if not key:
        return ""
    if len(key) <= 12:
        return "***"
    return key[:8] + "..." + key[-4:]


# ── 任务存储 ──

jobs = {}  # job_id -> {status, progress, result, error, current_chunk, ...}
jobs_lock = threading.Lock()  # 保护全局 jobs 字典的并发读写（#2）

TEMP_DIR = Path(tempfile.gettempdir()) / "video_analyzer"

TEMP_DIR.mkdir(exist_ok=True)



app = Flask(__name__, static_folder='.')

# CORS 白名单：仅允许本地前端页面来源（#4）
_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8765",
    "http://localhost:8765",
]
CORS(app, origins=_ALLOWED_ORIGINS, supports_credentials=False)



@app.route("/")

def index():

    return send_from_directory(".", "web_player.html")



@app.route("/web_player.html")

def web_player():

    return send_from_directory(".", "web_player.html")



# ── 工具 ──

def _quote(s):

    """Windows 安全路径引号（处理含空格路径）"""

    s = str(s)

    if ' ' in s or '"' in s:

        return '"' + s.replace('"', '\\"') + '"'

    return s



# ── 音频提取（用 imageio-ffmpeg，不依赖系统 ffmpeg）──

def extract_audio(video_path: str, wav_path: str, duration: float) -> bool:

    """

    用 imageio-ffmpeg 提取音频为 WAV（16kHz 单声道）。

    Whisper 最喜欢这种格式，后续可用 soundfile 直接读取为 numpy 数组。

    返回 True=成功，False=失败。

    """

    ffmpeg = get_ffmpeg()

    timeout = max(300, int(duration * 3) + 30)  # #4 安全下限 300s

    cmd_list = [

        ffmpeg,

        "-y",

        "-i", video_path,

        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",

        "-t", str(duration),

        wav_path,

    ]

    print(f"[Audio] 提取音频: {' '.join(cmd_list)[:200]}")

    try:

        result = subprocess.run(

            cmd_list,

            capture_output=True,

            text=True,

            timeout=timeout,

            encoding="utf-8", errors="replace",

            shell=False,  # #4 改为列表参数 + shell=False，避免命令注入

        )

        if result.returncode == 0 and os.path.exists(wav_path):

            size_kb = os.path.getsize(wav_path) / 1024

            print(f"[Audio] 提取成功: {wav_path} ({size_kb:.1f}KB)")

            return True

        else:

            print(f"[Audio] FFmpeg 失败 (rc={result.returncode}): {result.stderr[:500]}")

            return False

    except subprocess.TimeoutExpired:

        print("[Audio] FFmpeg 超时")

        return False

    except Exception as e:

        print(f"[Audio] 异常: {e}")

        return False



# ── 分片转写（真实进度，无需系统 ffmpeg）──

CHUNK_SECONDS = 10.0  # 每段 10 秒



def transcribe_audio_chunked(wav_path: str, duration: float, job_id: str):

    """

    将 WAV 用 soundfile 读取为 numpy 数组，按时间分片，

    逐段传给 model.transcribe(audio=array)，每段完成后更新真实进度。

    返回标准 transcript dict: {text, language, segments}

    """

    import numpy as np

    import soundfile as sf



    model = get_whisper_model()



    # 用 soundfile 读取 WAV（绕过 Whisper 的 load_audio → ffmpeg 调用）

    data, sr = sf.read(wav_path)

    if len(data.shape) > 1:

        data = data.mean(axis=1)  # 立体声转单声道

    assert sr == 16000, f"采样率应为 16000，实际为 {sr}"

    total_samples = len(data)

    total_duration = total_samples / sr



    # 计算分片数

    chunk_samples = int(sr * CHUNK_SECONDS)

    n_chunks = max(1, (total_samples + chunk_samples - 1) // chunk_samples)



    print(f"[Transcribe] 分片转写: {n_chunks} 段, 总长 {total_duration:.1f}s")



    all_segments = []

    all_texts = []

    initial_prompt_str = ""   # 用上一段末尾文字保持上下文



    for chunk_idx in range(n_chunks):

        start_sample = chunk_idx * chunk_samples

        end_sample = min(start_sample + chunk_samples, total_samples)

        chunk_data = data[start_sample:end_sample].astype(np.float32)

        start_sec = start_sample / sr

        end_sec = end_sample / sr



        # 更新进度（40% ~ 80% 映射到各分片）

        progress = 40.0 + (chunk_idx / n_chunks) * 40.0

        with jobs_lock:
            jobs[job_id]["progress"] = round(progress, 1)
            jobs[job_id]["current_chunk"] = f"第 {chunk_idx+1}/{n_chunks} 段 ({start_sec:.0f}s-{end_sec:.0f}s)"

        print(f"[Chunk {chunk_idx+1}/{n_chunks}] {start_sec:.0f}s-{end_sec:.0f}s progress={progress:.0f}%")



        if len(chunk_data) < sr * 0.5:

            print(f"[Chunk {chunk_idx+1}] 音频段过短（{len(chunk_data)/sr:.2f}s），跳过")

            continue



        # 转写本段（直接传 numpy 数组，Whisper 不会调 ffmpeg）

        try:

            print(f"[Chunk {chunk_idx+1}] 开始转写: shape={chunk_data.shape}, dtype={chunk_data.dtype}, 时长={len(chunk_data)/sr:.1f}s", flush=True)

            with open('transcribe_debug.log', 'a', encoding='utf-8') as f:

                f.write(f"[Chunk {chunk_idx+1}] 开始转写: shape={chunk_data.shape}, dtype={chunk_data.dtype}\n")

            result = model.transcribe(

                chunk_data,

                language="zh",

                task="transcribe",

                verbose=False,

                word_timestamps=False,

                fp16=False,

                initial_prompt=initial_prompt_str,

            )

            print(f"[Chunk {chunk_idx+1}] 转写完成: text='{result.get('text','')[:50]}...", flush=True)

            with open('transcribe_debug.log', 'a', encoding='utf-8') as f:

                f.write(f"[Chunk {chunk_idx+1}] 转写完成: {result.get('text','')[:50]}\n")

        except Exception as e:

            print(f"[Chunk {chunk_idx+1}] 转写失败: {e}", flush=True)

            import traceback; traceback.print_exc()

            continue



        # 收集结果（调整时间戳为视频绝对时间）

        for seg in result.get("segments", []):

            text = seg.get("text", "").strip()

            if text:

                all_segments.append({

                    "start": round(seg.get("start", 0) + start_sec, 2),

                    "end":   round(seg.get("end", 0) + start_sec, 2),

                    "text":  text,

                })



        chunk_text = result.get("text", "").strip()

        all_texts.append(chunk_text)



        # 用本段最后几个字作为下段的 initial_prompt（保持上下文连贯）

        segs = result.get("segments", [])

        if segs:

            last_text = segs[-1].get("text", "").strip()

            if last_text:

                initial_prompt_str = last_text[-15:]  # 取最后 15 个字符



    full_text = " ".join(t for t in all_texts if t)

    print(f"[Transcribe] 完成: {len(all_segments)} 段, 文本长度 {len(full_text)}")



    return {

        "text": full_text,

        "language": "zh",

        "segments": all_segments,

    }



# ── 音频特征分析 ──

def analyze_audio_features(wav_path: str) -> dict:

    """分析音频特征：能量、静音比、时间线"""

    try:

        import numpy as np

        import soundfile as sf

        data, sr = sf.read(wav_path)

        if len(data.shape) > 1:

            data = data.mean(axis=1)

        duration = len(data) / sr

        rms = float(np.sqrt(np.mean(data**2)))

        silence_ratio = float(np.sum(data**2 < 0.001) / len(data))

        chunk_size = int(sr * 0.5)

        energies = []

        for i in range(0, len(data), chunk_size):

            chunk = data[i:i+chunk_size]

            energies.append(float(np.sqrt(np.mean(chunk**2))))

        return {

            "duration": round(duration, 2),

            "rms": round(rms, 4),

            "silence_ratio": round(silence_ratio, 3),

            "has_audio": rms > 0.001,

            "energy_timeline": [round(e, 4) for e in energies[:60]],

        }

    except ImportError:

        return {"error": "soundfile/numpy 未安装"}

    except Exception as e:

        return {"error": str(e)}





def to_simplified(text: str) -> str:

    """繁体中文转简体中文（使用 zhconv）"""

    if not text:

        return text

    try:

        return zhconv.convert(text, 'zh-cn')

    except Exception as e:

        print(f"[Simplify] 转换失败: {e}")

        return text





def extract_keywords(text: str) -> dict:

    """从转写文本中提取关键词（后端版）"""

    if not text:

        return {"highFreq": [], "actions": [], "emotions": [], "products": []}



    ACTION_WORDS = set('推荐 介绍 讲解 分享 展示 演示 告诉 帮助 发现 觉得 看到 注意 开始 使用 体验 感受 操作 完成 点击 打开 购买 怎么 如何 为什么'.split())

    EMOTION_WORDS = set('非常 特别 真的 简直 太 好 很 超 极 十分 喜欢 爱 赞 棒 厉害 牛 优秀 完美 漂亮 好看 开心 快乐 激动 兴奋 惊喜 满意 放心 绝绝子 太棒 超级'.split())

    STOP = set('的是 这个 那个 就是 可以 没有 什么 怎么 一个 如果 因为 所以 而且 但是 或者 以及 还有 对于 关于 通过 进行'.split())



    import re

    words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)

    freq = {}

    for w in words:

        freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: -x[1])



    highFreq = [w for w, c in sorted_words if len(w) >= 2 and w not in STOP and c >= 2][:20]

    actions = [w for w, c in sorted_words if w in ACTION_WORDS][:10]

    emotions = [w for w, c in sorted_words if w in EMOTION_WORDS or any(e in w for e in EMOTION_WORDS)][:10]

    products = [w for w, c in sorted_words if len(w) >= 3 and w not in STOP][:15]



    return {

        "highFreq": highFreq,

        "actions": actions,

        "emotions": emotions,

        "products": products,

    }



# ── 转写任务入口（在新线程中运行）──

def run_transcription(job_id: str, video_path: str, duration: float):

    try:

        with jobs_lock:
            job = jobs[job_id]

        job["status"] = "extracting"
        job["progress"] = 10



        # 1. 提取音频

        wav_path = str(TEMP_DIR / f"{job_id}.wav")

        ok = extract_audio(video_path, wav_path, duration)



        if not ok or not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:

            # 检查是否是静音视频（无音轨）

            try:

                import imageio_ffmpeg

                ff = imageio_ffmpeg.get_ffmpeg_exe()

                check = subprocess.run(

                    [ff, "-i", video_path, "-map", "0:a", "-f", "null", "-"],

                    capture_output=True, text=True, timeout=300,

                    shell=False, encoding="utf-8", errors="replace",  # #4

                )

                no_audio = '0 streams' in check.stderr or 'does not contain' in check.stderr

            except:

                no_audio = False

            job["status"] = "no_audio"

            job["result"] = {

                "text": "",

                "segments": [],

                "error": "无法提取音频（该视频无音轨，为纯画面视频）" if no_audio else "无法提取音频（可能为静音视频）",

                "no_audio": True

            }

            job["progress"] = 100

            return



        job["status"] = "transcribing"
        job["progress"] = 40



        # 2. 分片转写（逐段更新真实进度 40%→80%）

        transcript = transcribe_audio_chunked(wav_path, duration, job_id)



        job["status"] = "analyzing"
        job["progress"] = 80



        # 3. 音频特征分析

        audio_features = analyze_audio_features(wav_path)



        # 4. 繁体→简体转换 + 关键词提取

        print("[PostProcess] 繁体转简体...")

        transcript["text"] = to_simplified(transcript.get("text", ""))

        for seg in transcript.get("segments", []):

            seg["text"] = to_simplified(seg.get("text", ""))



        print("[PostProcess] 提取关键词...")

        keywords = extract_keywords(transcript.get("text", ""))



        job["progress"] = 95



        # 5. 清理临时 WAV

        try:

            os.remove(wav_path)

        except:

            pass



        job["result"] = {**transcript, "audio_features": audio_features, "keywords": keywords}

        job["status"] = "done"

        job["progress"] = 100



    except Exception as e:

        import traceback

        traceback.print_exc()

        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["progress"] = 100

    finally:
        # 任务结束清理源视频与残留 WAV（#10）
        for _p in (video_path, str(TEMP_DIR / f"{job_id}.wav")):
            if _p and os.path.exists(_p):
                try:
                    os.remove(_p)
                except OSError:
                    pass



# ── API 路由 ──



@app.route("/api/transcribe", methods=["POST"])

def api_transcribe():

    if "video" not in request.files:

        return jsonify({"error": "缺少 video 文件"}), 400



    video_file = request.files["video"]

    duration = float(request.form.get("duration", 60))



    if not video_file.filename:

        return jsonify({"error": "文件名为空"}), 400



    job_id = str(uuid.uuid4())[:8]

    suffix = Path(video_file.filename).suffix or ".mp4"

    video_path = str(TEMP_DIR / f"{job_id}{suffix}")



    try:

        video_file.save(video_path)

        fsize = os.path.getsize(video_path)

        print(f"[Upload] {video_file.filename} -> {video_path} ({fsize/1024/1024:.2f}MB)")

    except Exception as e:

        return jsonify({"error": f"保存文件失败: {e}"}), 500



    with jobs_lock:
        jobs[job_id] = {

        "status": "starting",

        "progress": 0,

        "result": None,

        "error": None,

        "video_path": video_path,

        "duration": duration,

        "filename": video_file.filename,

        "current_chunk": "",

        }



    thread = threading.Thread(target=run_transcription, args=(job_id, video_path, duration), daemon=True)

    thread.start()



    return jsonify({

        "job_id": job_id,

        "status": "starting",

        "message": f"任务已创建，{video_file.filename} 正在转写中...",

    })



@app.route("/api/status/<job_id>")

def api_status(job_id):

    with jobs_lock:
        job = jobs.get(job_id)

    if not job:

        return jsonify({"error": "任务不存在"}), 404

    resp = {

        "job_id": job_id,

        "status": job["status"],

        "progress": job["progress"],

        "error": job.get("error"),

    }

    if job["status"] == "transcribing":

        resp["current_chunk"] = job.get("current_chunk", "")

    return jsonify(resp)



@app.route("/api/result/<job_id>")

def api_result(job_id):

    with jobs_lock:
        job = jobs.get(job_id)

    if not job:

        return jsonify({"error": "任务不存在"}), 404

    if job["status"] not in ("done", "error"):

        return jsonify({"error": "任务未完成", "status": job["status"], "progress": job["progress"]}), 202

    if job["status"] == "error":

        return jsonify({"error": job.get("error", "未知错误"), "status": "error"}), 500



    # 清理视频临时文件

    vp = job.get("video_path")

    if vp and os.path.exists(vp):

        try:

            os.remove(vp)

            print(f"[Cleanup] 删除临时视频: {vp}")

        except:

            pass



    return jsonify({"job_id": job_id, "status": "done", "result": job["result"]})



@app.route("/api/video-meta", methods=["GET", "POST"])

def api_video_meta():

    # GET: 健康检查

    if request.method == "GET":

        return jsonify({"status": "ok", "model": "tiny", "version": "1.0"})

    

    # POST: 上传视频获取元数据

    if "video" not in request.files:

        return jsonify({"error": "缺少 video 文件"}), 400



    video_file = request.files["video"]

    job_id = str(uuid.uuid4())[:8]

    suffix = Path(video_file.filename).suffix or ".mp4"

    video_path = str(TEMP_DIR / f"{job_id}{suffix}")



    try:

        video_file.save(video_path)

    except Exception as e:

        return jsonify({"error": f"保存失败: {e}"}), 500



    try:

        import cv2

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():

            return jsonify({"error": "无法读取视频文件"}), 400

        fps = cap.get(cv2.CAP_PROP_FPS)

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        duration = frame_count / fps if fps > 0 else 0

        cap.release()



        # 检查音轨

        has_audio = False

        try:

            import imageio_ffmpeg as iio

            probe_cmd = [get_ffmpeg(), "-i", video_path, "-hide_banner"]

            pr = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace", shell=False)  # #4

            out = pr.stderr + pr.stdout

            has_audio = "Audio:" in out

        except:

            pass



        fsize = os.path.getsize(video_path)

        try:

            os.remove(video_path)

        except:

            pass



        return jsonify({

            "fps": round(fps, 2),

            "frame_count": frame_count,

            "width": width,

            "height": height,

            "duration": round(duration, 2),

            "file_size_mb": round(fsize / 1024 / 1024, 2),

            "has_audio": has_audio,

        })

    except ImportError:

        return jsonify({"error": "opencv-python 未安装"}), 500

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({"error": str(e)}), 500





# ============================================================



@app.route("/health", methods=["GET"])
def health():
    """健康检查端点（#6），返回服务状态与当前 Whisper 模型名。"""
    return jsonify({"status": "ok", "whisper_model": _whisper_model_name})


# ============================================================
# 文案深度分析端点（需要 LLM API Key）
# ============================================================


def call_llm_analyze(input_data_str, api_key=None, base_url=None, model_name=None,
                     provider=None, ollama_base=None):
    import requests
    provider = (provider or "").strip().lower()
    # 前端传入的 key 优先，否则读环境变量
    api_key = api_key or os.environ.get("LLM_API_KEY", "")
    # 日志只输出脱敏后的 Key（#5）
    print(f"[LLM] provider={provider} key={mask_key(api_key)}")
    base_url = base_url or os.environ.get("LLM_BASE_URL", "")
    if not api_key and provider != "ollama":
        return {"error": "请先填入 API Key", "available": False}
    # 服务商判定：显式 provider 优先，否则按 key 前缀自动检测
    is_siliconflow = (provider == "siliconflow") or (
        not provider and ("siliconflow" in base_url.lower()
                          or (not base_url and len(api_key) > 30 and api_key.startswith("sk-")))
    )
    if is_siliconflow:
        base_url = "https://api.siliconflow.cn/v1/chat/completions"
    elif not base_url:
        base_url = os.environ.get(
            "LLM_BASE_URL",
            "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        )
    headers_dict = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
    system_prompt = (
        "你是一位专业的短视频内容分析专家。请严格按照九节格式输出结构化报告，"
        "用Markdown格式，包含所有表格，每节必须有实质内容。"
    )
    user_prompt_lines = [
        "你是一位顶尖的短视频带货文案拆解专家，擅长将口播文案拆解为结构统一、颗粒度到秒、可直接指导编导复刻的标准化报告。",
        "",
        "## 输入数据",
        "INPUT_DATA_PLACEHOLDER",
        "",
        "## 任务",
        "严格按照以下九节结构输出，每节必须有实质内容，不允许参照原文或此处省略。",
        "",
        "### 一句话总结（一行）",
        "格式：核心结论 · 流量打法 · 叙事主权破局点，三点用箭头连接。",
        "",
        "### 第一节 · 原文基础信息",
        "- 逐字稿全文（保留原文，只做繁转简）",
        "- 表层口播逻辑：用箭头连接，不超过6步",
        "",
        "### 第二节 · 深度反向拆解",
        "- 风格调性（1句话）",
        "- 观众心理路径（时间顺序，3到5个转折点）",
        "- 3到5条可迁移底层情绪（人性驱动，不是表面技巧）",
        "- 叙事主权4步拆解：",
        "  1. 破霸权：具体是什么谎言或霸权",
        "  2. 建标准：用什么事实或数据重建标准",
        "  3. 立人设：主角的人设是什么",
        "  4. 收闭环：怎么把情绪转化为信任",
        "- 跑量优势（3条，简短）",
        "",
        "### 第三节 · 口播逐段拆解",
        "用表格输出，包含：预估时长、内容模块、原文内容、核心作用、叙事主权标注、算法增益、5A标注。",
        "模块分类：开场钩子、产品介绍、效果展示、信任背书、行动召唤、其他。",
        "叙事主权标注：破霸权、建标准、立人设、收闭环。",
        "算法增益：完播驱动、点赞驱动、评论驱动、分享驱动、关注驱动。",
        "5A标注：A1（3秒）、A2（前三分位）、A3（中段）、A4（后三分位）、A5（结尾）。",
        "",
        "### 第四节 · 分镜头拆解",
        "用表格输出，包含：镜头编号、时长、景别加运镜、画面内容、对应口播、情绪流转、视觉实锤。",
        "景别：特写、近景、中景、全景、远景、文字展示。运镜：固定、推进、拉远、摇镜、跟拍、升降。",
        "视觉实锤：具体画面细节，不允许省略。",
        "",
        "### 第五节 · 5A人群流转",
        "用表格输出，包含：人群层级、作用强度（1到5星）、核心流转价值、完整流转路径。",
        "",
        "### 第六节 · 爆款文案库",
        "用表格输出，包含：文案分类、文案内容、预估转化率、预估完播率、使用场景。",
        "每模块至少3条替代文案，保持原文人设语气。",
        "文案分类：开场钩子、产品卖点、效果描述、信任背书、行动召唤。",
        "",
        "### 第七节 · 可复刻对标行业",
        "3到5个相邻品类，每条格式：推翻 X 旧叙事、然后建立 Y 新标准。",
        "",
        "### 第八节 · 团队落地执行要点",
        "5到6条，每条一条可执行指令。",
        "- 【叙事一致性】：……",
        "- 【实锤优先】：……",
        "- 【背书强化】：……",
        "- 【反攻击预案】：……",
        "- 【人群侧重】：……",
        "- 【分镜实操】：……",
        "",
        "## 约束",
        "- 基于原文事实，不编造数据；缺失信息用【推断】标注",
        "- 时间轴秒级，覆盖率100%，不允许其余部分同理",
        "- 替代文案语气和情绪强度与原文一致，不可降维",
        "- 全部用Markdown标准表格输出",
    ]
    user_prompt_lines[3] = input_data_str
    user_prompt = "\n".join(user_prompt_lines)

    # ── Ollama 本地模型（无需 API Key） ──
    if provider == "ollama":
        base = (ollama_base or os.environ.get("OLLAMA_BASE", "http://localhost:11434")).rstrip("/")
        model = model_name or os.environ.get("LLM_MODEL", "llama3.1")
        try:
            resp = requests.post(base + "/api/chat", json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.3},
            }, timeout=300)
            if resp.status_code == 200:
                odata = resp.json()
                content = odata.get("message", {}).get("content", "")
                return {"report": content, "available": True, "model": model}
            return {"error": "Ollama HTTP " + str(resp.status_code) + ": " + resp.text[:300],
                    "available": True, "model": model}
        except Exception as e:
            return {"error": "Ollama 连接失败（" + base + "）：" + str(e), "available": True}

    # SiliconFlow 默认用 Qwen2.5-72B，智谱默认 glm-4-flash
    if is_siliconflow:
        model = model_name or os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")
    else:
        model = model_name or os.environ.get("LLM_MODEL", "glm-4-flash")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
    }
    try:
        resp = requests.post(
            base_url,
            headers=headers_dict, json=payload, timeout=180,
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"report": content, "available": True, "model": model}
        else:
            return {
                "error": "API error " + str(resp.status_code) + ": " + resp.text[:200],
                "available": True,
            }
    except Exception as e:
        return {"error": str(e), "available": True}


@app.route("/api/analyze-copy", methods=["POST"])

def api_analyze_copy():

    try:

        body = request.get_json()

    except Exception:

        return jsonify({"error": "Invalid JSON body"}), 400

    transcription = body.get("transcription", {})

    analysis = body.get("analysis", {})

    video_meta = body.get("video_meta", {})

    provider = (body.get("provider") or "").strip().lower()

    ollama_base = (body.get("ollama_base") or "").strip()

    api_key = body.get("api_key", "") or None

    full_text = transcription.get("text", "") or transcription.get("fullText", "")

    if not full_text:

        return jsonify({"error": "No transcription text available"}), 400

    if provider != "ollama" and not api_key:

        return jsonify({"error": "请先填入 API Key", "available": False}), 400

    segments = transcription.get("segments", [])

    seg_lines = []

    for s in segments:

        seg_lines.append(f"[{s.get('start',0):.1f}s-{s.get('end',0):.1f}s] {s.get('text','')}")

    seg_text = "\n".join(seg_lines)

    content_type = analysis.get("contentType", {}) or {}

    frames = analysis.get("frames", [])

    frame_summary = []

    for f in frames[:20]:

        frame_summary.append(

            f"- {f.get('t',0):.1f}s | 亮度:{round(f.get('brightness',0),3)} "

            f"| 主色:{f.get('dominantColor','N/A')} | 景别:{f.get('shotType','N/A')} "

            f"| 字幕:{'有' if f.get('textRatio',0)>5 else '无'} "

            f"| 人物:{'有' if f.get('skinRatio',0)>0.05 else '无'}"

        )

    phase_lines = []

    for p in analysis.get("phases", []):

        phase_lines.append(

            f"- {p.get('label','')} "

            f"(@{p.get('start',0):.0f}s-{p.get('end',0):.0f}s, "

            f"{p.get('end',0)-p.get('start',0):.1f}秒)"

        )

    kw = transcription.get("keywords", {}) or {}

    input_data = (

        "【视频基本信息】\n"

        f"- 文件名：{analysis.get('name','未知')}\n"

        f"- 时长：{analysis.get('duration',0):.1f}秒\n"

        f"- 分辨率：{video_meta.get('width',0)}x{video_meta.get('height',0)}\n"

        f"- 内容类型：{content_type.get('label','未知')} — {content_type.get('desc','')}\n\n"

        "【逐字稿（按时间分段）】\n"

        + seg_text +

        "\n\n【帧画面摘要（前20帧）】\n"

        + "\n".join(frame_summary) +

        "\n\n【场景分段】\n"

        + "\n".join(phase_lines) +

        "\n\n【关键词】\n"

        f"高频词：{kw.get('highFreq',[])[:20]}\n"

        f"动作词：{kw.get('actions',[])[:10]}\n"

        f"情绪词：{kw.get('emotions',[])[:10]}\n"

    )

    result = call_llm_analyze(
        input_data,
        api_key=api_key,
        provider=provider,
        ollama_base=ollama_base,
        model_name=body.get("model") or None,
    )

    return jsonify({

        "status": "ok",

        "has_llm": result.get("available", False),

        "report": result.get("report", None),

        "error": result.get("error", None),

        "segments_count": len(segments),

        "frames_count": len(frames),

        "full_text_length": len(full_text),

        "model": result.get("model", None)

    })







# ── API Key 验证端点 ──
@app.route("/api/test-api-key", methods=["POST"])
def api_test_api_key():
    import requests as _req
    try:
        body = request.get_json() or {}
    except Exception:
        return jsonify({"ok": False, "error": "Invalid JSON body"}), 400

    api_key = (body.get("api_key") or "").strip()
    model   = (body.get("model")   or "").strip()
    provider = (body.get("provider") or "").strip().lower()
    ollama_base = (body.get("ollama_base") or os.environ.get("OLLAMA_BASE", "http://localhost:11434")).strip()
    print(f"[APIKey] 验证请求: provider={provider} key={mask_key(api_key)}")

    # ── Ollama 本地模型（无需 API Key） ──
    if provider == "ollama":
        try:
            resp = _req.get(ollama_base.rstrip("/") + "/api/tags", timeout=10)
            if resp.status_code == 200:
                mlist = resp.json().get("models", [])
                models = []
                for m in mlist:
                    name = m.get("name") or m.get("model") or ""
                    if name:
                        models.append([name, name])
                if not models:
                    return jsonify({
                        "ok": False,
                        "error": "Ollama 已连接（" + ollama_base + "），但本地没有模型。请用 `ollama pull <模型名>` 拉取，例如：ollama pull llama3.1",
                        "available_models": [],
                    })
                return jsonify({
                    "ok": True,
                    "model": models[0][0],
                    "provider": "Ollama",
                    "available_models": models,
                    "ollama_base": ollama_base,
                })
            return jsonify({
                "ok": False,
                "error": "Ollama 返回 HTTP " + str(resp.status_code) + "：" + resp.text[:200],
                "available_models": [],
            })
        except _req.exceptions.Timeout:
            return jsonify({
                "ok": False,
                "error": "连接 Ollama 超时（10秒）：" + ollama_base + "。请确认 Ollama 已启动（ollama serve）。",
                "available_models": [],
            })
        except Exception as e:
            return jsonify({
                "ok": False,
                "error": "无法连接 Ollama（" + ollama_base + "）：" + str(e) + "。请确认 Ollama 已启动。",
                "available_models": [],
            })

    if not api_key:
        return jsonify({"ok": False, "error": "API Key 不能为空"})

    # 服务商判定：显式 provider 优先，否则按 key 前缀自动检测
    is_sf = (provider == "siliconflow") or (not provider and api_key.startswith("sk-"))
    if is_sf:
        base_url = "https://api.siliconflow.cn/v1/chat/completions"
        models = [
            ("Qwen/Qwen2.5-72B-Instruct",       "Qwen2.5-72B（推荐·效果最好）"),
            ("deepseek-ai/DeepSeek-V2.5",       "DeepSeek V2.5（性价比）"),
            ("deepseek-ai/DeepSeek-V3",         "DeepSeek V3"),
            ("Qwen/Qwen2.5-14B-Instruct",       "Qwen2.5-14B"),
            ("Qwen/Qwen2.5-7B-Instruct",        "Qwen2.5-7B（速度快）"),
            ("THUDM/glm-4-9b-chat",             "GLM-4-9B"),
            ("iic/llama3.1-8b-instruct",        "Llama3.1-8B"),
            ("iic/qwen2-7b-instruct",           "Qwen2-7B"),
        ]
        default_model = "Qwen/Qwen2.5-72B-Instruct"
    else:
        base_url = os.environ.get(
            "LLM_BASE_URL",
            "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        )
        models = [
            ("glm-4-flash",  "GLM-4-Flash（默认·推荐）"),
            ("glm-4",        "GLM-4"),
            ("glm-4-plus",   "GLM-4-Plus"),
        ]
        default_model = "glm-4-flash"

    test_model = model if model else default_model

    payload = {
        "model": test_model,
        "messages": [{"role": "user", "content": "你好，返回 OK。"}],
        "max_tokens": 10,
        "temperature": 0,
    }

    try:
        resp = _req.post(
            base_url,
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            return jsonify({
                "ok": True,
                "model": test_model,
                "provider": "SiliconFlow" if is_sf else "Zhipu/Other",
                "available_models": models,
            })
        else:
            err = resp.text[:200]
            return jsonify({
                "ok": False,
                "error": "HTTP " + str(resp.status_code) + ": " + err,
                "available_models": models,
            })
    except _req.exceptions.Timeout:
        return jsonify({
            "ok": False,
            "error": "请求超时（30秒），请检查网络或换用更快的模型",
            "available_models": models,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "available_models": models})



# ── 启动 ──

def _cleanup_old_temp_files(max_age_hours: float = 1.0):
    """启动时清理超过 1 小时的临时文件（#10）"""
    try:
        now = time.time()
        for p in TEMP_DIR.glob("*"):
            try:
                if p.is_file() and (now - p.stat().st_mtime) > max_age_hours * 3600:
                    p.unlink()
            except OSError:
                pass
    except Exception:
        pass


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Video Content Analyzer Backend")

    parser.add_argument("--host", default="0.0.0.0", help="监听地址")

    parser.add_argument("--port", type=int, default=8766, help="监听端口")

    parser.add_argument("--model", default="tiny", choices=["tiny", "base", "small", "medium"], help="Whisper 模型")
    args = parser.parse_args()
    _whisper_model_name = args.model


    print(f"""

╔══════════════════════════════════════════════════════════════╗

║   Video Content Analyzer Backend                              ║

║   转写服务  http://{args.host}:{args.port}                        ║

║   转写模式  分片逐段（真实进度条 40%→80%，无需系统 ffmpeg）║

╚══════════════════════════════════════════════════════════════╝

  Whisper 模型 : {args.model}

  音频格式     : WAV 16kHz 单声道（soundfile 直读，不调 ffmpeg）

  分片大小     : {CHUNK_SECONDS} 秒/段

  依赖         : imageio-ffmpeg（音频提取）+ soundfile（Whisper 输入）

""")

    # Print LAN access URL

    if args.host == '0.0.0.0':

        import socket

        s = None

        try:

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            s.connect(('8.8.8.8', 1))

            ip = s.getsockname()[0]

            print(f'  LAN access: http://{ip}:{args.port}')

        except Exception:

            pass

        finally:

            if s is not None:

                s.close()

    

    _cleanup_old_temp_files()  # 启动时清理过期临时文件（#10）

    app.run(host=args.host, port=args.port, debug=False, threaded=True)



