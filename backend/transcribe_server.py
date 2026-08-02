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

_whisper_models = {}  # key "model_name#instance_id" -> model instance
_whisper_model_lock = threading.Lock()
_whisper_model_name = "small"  # default, overridden by --model arg
_ffmpeg_exe = None

# 可选模型列表（前端下拉框用）
WHISPER_MODEL_CHOICES = [
    ("tiny", "Tiny — 最快(约5x)，适合快速预览"),
    ("base", "Base — 快速(约3x)，平衡速度与质量"),
    ("small", "Small — 默认，中文识别较好"),
    ("medium", "Medium — 最慢但最准确"),
]



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



def get_whisper_model(model_name=None, instance_id=0, num_threads=None):

    """懒加载 Whisper 模型，支持多模型缓存和并行实例"""

    global _whisper_models

    if model_name is None:

        model_name = _whisper_model_name

    key = f"{model_name}#{instance_id}"

    if key not in _whisper_models:

        with _whisper_model_lock:

            if key not in _whisper_models:

                import whisper

                if num_threads is not None:
                    try:
                        import torch
                        torch.set_num_threads(num_threads)
                        print(f"[Whisper] torch 线程数设为 {num_threads}")
                    except Exception:
                        pass

                print(f"[Whisper] 加载 {model_name} 模型 (实例 {instance_id})...")

                t0 = time.time()
                _whisper_models[key] = whisper.load_model(model_name, device="cpu")
                t1 = time.time()

                print(f"[Whisper] {model_name} 加载完成 (实例 {instance_id}, 耗时 {t1-t0:.1f}s, 总缓存: {len(_whisper_models)})")

    return _whisper_models[key]



# ── 任务存储 ──

jobs = {}  # job_id -> {status, progress, result, error, current_chunk, ...}

analyze_jobs = {}  # job_id -> {status, progress, result, error, model}

TEMP_DIR = Path(tempfile.gettempdir()) / "video_analyzer"

TEMP_DIR.mkdir(exist_ok=True)



BASE_DIR = Path(__file__).resolve().parent          # 本文件所在目录 (backend/)
FRONTEND_DIR = BASE_DIR.parent / "frontend"         # Projects/video-analyzer/frontend
EXPORT_DIR = BASE_DIR.parent / "exports"            # Projects/video-analyzer/exports
EXPORT_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(FRONTEND_DIR))

_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8766",
    "http://localhost:8766",
    "http://192.168.0.8:8766",
    "http://192.168.0.24:8766",
]
CORS(app, origins=_ALLOWED_ORIGINS)



@app.after_request
def add_no_cache_headers(response):
    """禁止浏览器缓存前端文件，确保每次拿到最新版本"""
    if response.content_type and (
        'text/html' in response.content_type
        or 'application/javascript' in response.content_type
        or 'text/css' in response.content_type
        or 'text/plain' in response.content_type
    ):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


@app.route("/")

def index():

    return send_from_directory(str(FRONTEND_DIR), "web_player.html")



@app.route("/web_player.html")

def web_player():

    return send_from_directory(str(FRONTEND_DIR), "web_player.html")


@app.route("/favicon.ico")
def favicon():
    from flask import Response
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
           '<rect width="32" height="32" rx="6" fill="#4F46E5"/>'
           '<text x="16" y="23" text-anchor="middle" font-size="20" fill="white">V</text>'
           '</svg>')
    return Response(svg, mimetype="image/svg+xml")


@app.route("/chart.umd.min.js")
def chart_js():
    return send_from_directory(str(FRONTEND_DIR), "chart.umd.min.js")

@app.route("/jszip.min.js")
def jszip_js():
    return send_from_directory(str(FRONTEND_DIR), "jszip.min.js")



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
    用 imageio-ffmpeg 提取音频，通过管道输出 raw PCM，
    再由 soundfile 写入格式正确的 WAV。
    避免 Windows 下 ffmpeg -t 截断导致 RIFF 头不完整、soundfile 报 Invalid argument 的问题。
    返回 True=成功，False=失败。
    """
    import numpy as np
    import soundfile as sf

    # duration 异常保护（NaN / <=0 / 非数值）：避免 int(duration*3) 抛 ValueError
    if not isinstance(duration, (int, float)) or duration <= 0 or duration != duration:
        duration = 60.0

    ffmpeg = get_ffmpeg()
    timeout = max(60, int(duration * 3) + 30)

    # 直接让 ffmpeg 写出标准 PCM16 WAV 文件（不再经 numpy + soundfile 写 float WAV）。
    # 这绕开了 Windows 下 libsndfile 写/读 float WAV 偶发 [Errno 22] Invalid argument 的问题；
    # ffmpeg 封装的 PCM16 WAV 是 libsndfile 兼容性最佳的格式，后续 soundfile 只读不写。
    cmd = (
        f'{_quote(ffmpeg)} -y '
        f'-i {_quote(video_path)} '
        f'-vn -acodec pcm_s16le -ar 16000 -ac 1 '
        f'-t {duration} '
        f'{_quote(wav_path)}'
    )

    print(f"[Audio] 提取音频 (ffmpeg->wav): {cmd[:200]}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            shell=True  # Windows 必须 shell=True 才能找到 imageio-ffmpeg 路径
        )

        if result.returncode != 0 or not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
            err_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
            print(f"[Audio] FFmpeg 失败 (rc={result.returncode}): {err_msg[:500]}")
            return False

        # 校验：soundfile 只读少量帧，确认 WAV 可被正常打开（封装正确）
        try:
            _v = sf.read(wav_path, frames=16000)
            if len(_v[0]) == 0:
                print("[Audio] 校验失败：WAV 无音频样本")
                return False
        except Exception as ve:
            print(f"[Audio] 校验异常: {ve}")
            return False
        size_kb = os.path.getsize(wav_path) / 1024
        print(f"[Audio] 提取成功: {wav_path} ({size_kb:.1f}KB)")

        return True

    except subprocess.TimeoutExpired:
        print("[Audio] FFmpeg 超时")
        return False

    except Exception as e:
        print(f"[Audio] 异常: {e}")
        return False



# ── 分片转写（真实进度，无需系统 ffmpeg）──

CHUNK_SECONDS = 15.0  # 每段 15 秒（平衡并行度与调度开销）



def transcribe_audio_chunked(wav_path: str, duration: float, job_id: str, model_name: str = None):

    """

    将 WAV 用 soundfile 读取为 numpy 数组，按时间分片，

    并行传给 model.transcribe(audio=array)，每段完成后更新真实进度。

    返回标准 transcript dict: {text, language, segments}

    """

    import numpy as np

    import soundfile as sf

    import queue as queue_mod

    from concurrent.futures import ThreadPoolExecutor, as_completed



    if model_name is None:

        model_name = _whisper_model_name



    # 用 soundfile 读取 WAV（绕过 Whisper 的 load_audio → ffmpeg 调用）
    try:
        data, sr = sf.read(wav_path)
    except Exception as re:
        raise RuntimeError(f"音频解码失败：WAV 无法读取（可能音频格式不支持或文件损坏）: {re}")

    if len(data.shape) > 1:

        data = data.mean(axis=1)  # 立体声转单声道

    assert sr == 16000, f"采样率应为 16000，实际为 {sr}"

    total_samples = len(data)

    total_duration = total_samples / sr



    # 计算分片数

    chunk_samples = int(sr * CHUNK_SECONDS)

    n_chunks = max(1, (total_samples + chunk_samples - 1) // chunk_samples)



    print(f"[Transcribe] 并行分片转写: {n_chunks} 段, 总长 {total_duration:.1f}s, 模型={model_name}")



    # 预切分所有分片

    chunks_info = []

    for chunk_idx in range(n_chunks):

        start_sample = chunk_idx * chunk_samples

        end_sample = min(start_sample + chunk_samples, total_samples)

        chunk_data = data[start_sample:end_sample].astype(np.float32)

        start_sec = start_sample / sr

        end_sec = end_sample / sr

        if len(chunk_data) < sr * 0.5:

            print(f"[Chunk {chunk_idx+1}] 音频段过短（{len(chunk_data)/sr:.2f}s），跳过")

            continue

        chunks_info.append((chunk_idx, chunk_data, start_sec, end_sec))



    n_valid = len(chunks_info)

    # 检测 CPU 核心数
    try:
        import multiprocessing as mp
        cpu_count = mp.cpu_count()
    except Exception:
        cpu_count = 8

    # 并行度决策：tiny/base 用 3 线程，small 用 2 线程，medium 用 1 线程
    if model_name in ("tiny", "base"):
        max_workers = min(n_valid, 3)
    elif model_name == "small":
        max_workers = min(n_valid, 2)
    else:
        max_workers = 1

    # 智能降级：仅 1 段时用单线程（多实例加载开销不值得）
    if n_valid <= 1:
        max_workers = 1

    # 动态计算每个 worker 的 torch 线程数，避免超额订阅
    threads_per_worker = max(1, cpu_count // max_workers) if max_workers > 0 else cpu_count

    print(f"[Transcribe] 并行度: {max_workers} 线程, {n_valid} 个有效分片, "
          f"CPU={cpu_count}核, torch={threads_per_worker}线程/worker, "
          f"总线程={max_workers * threads_per_worker}")



    # 模型实例池（每个线程用独立实例，避免线程安全问题）

    model_pool = queue_mod.Queue()

    for i in range(max_workers):

        if i == 0:
            jobs[job_id]["progress"] = 18
            jobs[job_id]["detail"] = f"正在加载 Whisper 模型（{model_name}，实例 {i+1}/{max_workers}）..."

        model_pool.put(get_whisper_model(model_name, i, num_threads=threads_per_worker))

    jobs[job_id]["progress"] = 22
    jobs[job_id]["detail"] = f"模型加载完成，开始转写 {n_valid} 个分片（{max_workers} 线程并行）..."



    # 单段转写函数（从池中取模型，用完归还）

    def _transcribe_one(c_idx, c_data, c_start, c_end):

        m = model_pool.get()

        try:

            print(f"[Chunk {c_idx+1}/{n_valid}] 开始转写: {c_start:.0f}s-{c_end:.0f}s, 时长={len(c_data)/sr:.1f}s", flush=True)

            result = m.transcribe(

                c_data,

                language="zh",

                task="transcribe",

                verbose=False,

                word_timestamps=False,

                fp16=False,

            )

            print(f"[Chunk {c_idx+1}] 完成: '{result.get('text','')[:50]}...'", flush=True)

            return c_idx, result

        except Exception as e:

            print(f"[Chunk {c_idx+1}] 转写失败: {e}", flush=True)

            import traceback; traceback.print_exc()

            return c_idx, {"text": "", "segments": []}

        finally:

            model_pool.put(m)  # 归还模型实例



    # 并行执行

    results = {}

    completed = 0

    t_transcribe_start = time.time()

    if max_workers <= 1:

        # 顺序模式（medium 模型或单分片）

        for c_idx, c_data, c_start, c_end in chunks_info:

            jobs[job_id]["current_chunk"] = f"第 {c_idx+1}/{n_valid} 段 ({c_start:.0f}s-{c_end:.0f}s)"

            jobs[job_id]["detail"] = f"正在转写第 {c_idx+1}/{n_valid} 段 ({c_start:.0f}s-{c_end:.0f}s)..."

            progress = 25.0 + (completed / n_valid) * 50.0

            jobs[job_id]["progress"] = round(progress, 1)

            r_idx, r_result = _transcribe_one(c_idx, c_data, c_start, c_end)

            results[r_idx] = (r_result, c_start)

            completed += 1

            progress = 25.0 + (completed / n_valid) * 50.0

            jobs[job_id]["progress"] = round(progress, 1)

            jobs[job_id]["detail"] = f"已完成 {completed}/{n_valid} 段"

    else:

        # 并行模式

        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            future_map = {}

            for c_idx, c_data, c_start, c_end in chunks_info:

                future = executor.submit(_transcribe_one, c_idx, c_data, c_start, c_end)

                future_map[future] = (c_idx, c_start)

            for future in as_completed(future_map):

                c_idx, c_start = future_map[future]

                r_idx, r_result = future.result()

                results[r_idx] = (r_result, c_start)

                completed += 1

                progress = 25.0 + (completed / n_valid) * 50.0

                jobs[job_id]["progress"] = round(progress, 1)

                jobs[job_id]["current_chunk"] = f"已完成 {completed}/{n_valid} 段"

                jobs[job_id]["detail"] = f"已完成 {completed}/{n_valid} 段"

                print(f"[Progress] {completed}/{n_valid} 完成, progress={progress:.0f}%")



    t_transcribe_end = time.time()
    print(f"[Transcribe] 转写阶段耗时: {t_transcribe_end - t_transcribe_start:.1f}s "
          f"({n_valid} 段, {max_workers} 线程, 平均 {((t_transcribe_end - t_transcribe_start) / max(n_valid, 1)):.1f}s/段)")



    # 合并结果（按原始顺序）

    all_segments = []

    all_texts = []

    for c_idx in sorted(results.keys()):

        result, start_sec = results[c_idx]

        for seg in result.get("segments", []):

            text = seg.get("text", "").strip()

            if text:

                all_segments.append({

                    "start": round(seg.get("start", 0) + start_sec, 2),

                    "end":   round(seg.get("end", 0) + start_sec, 2),

                    "text":  text,

                })

        all_texts.append(result.get("text", "").strip())



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

    """从转写文本中提取关键词（后端版）：jieba 分词 + 词频统计"""

    if not text:

        return {"highFreq": [], "actions": [], "emotions": [], "products": []}

    ACTION_WORDS = set('推荐 介绍 讲解 分享 展示 演示 告诉 帮助 发现 觉得 看到 注意 开始 使用 体验 感受 操作 完成 点击 打开 购买 怎么 如何 为什么'.split())

    EMOTION_WORDS = set('非常 特别 真的 简直 太 好 很 超 极 十分 喜欢 爱 赞 棒 厉害 牛 优秀 完美 漂亮 好看 开心 快乐 激动 兴奋 惊喜 满意 放心 绝绝子 太棒 超级'.split())

    STOP = set('的是 这个 那个 就是 可以 没有 什么 怎么 一个 如果 因为 所以 而且 但是 或者 以及 还有 对于 关于 通过 进行 我们 你们 他们 大家 今天 现在 已经 真的 就是 一个 一下 起来 过来 什么 时候 自己 东西 时候 知道'.split())

    import re
    import jieba

    # jieba 分词，过滤单字/停用词/纯数字
    segs = jieba.lcut(text)
    words = []
    for w in segs:
        w = w.strip()
        if len(w) >= 2 and w not in STOP and not w.isdigit() and re.search(r'[\u4e00-\u9fa5A-Za-z]', w):
            words.append(w)

    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: (-x[1], len(x[0])))

    # 高频词：出现≥2次优先；不足时补齐出现1次的实词
    highFreq = [w for w, c in sorted_words if c >= 2][:20]
    if len(highFreq) < 8:
        for w, c in sorted_words:
            if w not in highFreq and len(w) >= 2:
                highFreq.append(w)
            if len(highFreq) >= 20:
                break

    # 动作词/情绪词：词级匹配优先，句子包含兜底（jieba 可能拆散）
    actions = []
    emotions = []
    for w in words:
        if w in ACTION_WORDS and w not in actions:
            actions.append(w)
        if w in EMOTION_WORDS and w not in emotions:
            emotions.append(w)

    sentences = [s.strip() for s in re.split(r'[。！？!?，,；;：:、\s\n]+', text) if len(s.strip()) >= 2]
    if len(actions) < 3:
        for s in sentences:
            for a in ACTION_WORDS:
                if a in s and a not in actions:
                    actions.append(a)
    if len(emotions) < 3:
        for s in sentences:
            for e in EMOTION_WORDS:
                if e in s and e not in emotions:
                    emotions.append(e)

    # 产品/核心词：实词，优先长词/高频
    products = [w for w, c in sorted_words if len(w) >= 2][:15]

    return {
        "highFreq": highFreq[:20],
        "actions": actions[:10],
        "emotions": emotions[:10],
        "products": products[:15],
    }



    return {

        "highFreq": highFreq,

        "actions": actions,

        "emotions": emotions,

        "products": products,

    }



# ── 转写任务入口（在新线程中运行）──

def run_transcription(job_id: str, video_path: str, duration: float, model_name: str = None):

    try:

        jobs[job_id]["status"] = "extracting"

        jobs[job_id]["progress"] = 8

        jobs[job_id]["detail"] = "正在提取音频..."



        # 1. 提取音频

        wav_path = str(TEMP_DIR / f"{job_id}.wav")

        ok = extract_audio(video_path, wav_path, duration)



        if not ok or not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:

            # 检查是否是静音视频（无音轨）

            try:

                import imageio_ffmpeg

                ff = imageio_ffmpeg.get_ffmpeg_exe()

                check = subprocess.run(

                    f'"{ff}" -i "{video_path}" -map 0:a -f null - 2>&1',

                    capture_output=True, text=True, timeout=10,

                    shell=True, encoding='utf-8', errors='replace'

                )

                no_audio = '0 streams' in check.stderr or 'does not contain' in check.stderr

            except:

                no_audio = False

            jobs[job_id]["status"] = "no_audio"

            jobs[job_id]["result"] = {

                "text": "",

                "segments": [],

                "error": "无法提取音频（该视频无音轨，为纯画面视频）" if no_audio else "无法提取音频（可能为静音视频）",

                "no_audio": True

            }

            jobs[job_id]["progress"] = 100

            jobs[job_id]["detail"] = "无音频"

            return



        jobs[job_id]["status"] = "transcribing"

        jobs[job_id]["progress"] = 15

        jobs[job_id]["detail"] = f"音频提取完成，正在加载 Whisper 模型（{model_name or _whisper_model_name}）..."



        # 2. 分片转写（逐段更新真实进度 20%→75%）

        transcript = transcribe_audio_chunked(wav_path, duration, job_id, model_name=model_name)



        jobs[job_id]["status"] = "analyzing"

        jobs[job_id]["progress"] = 80

        jobs[job_id]["detail"] = "转写完成，正在分析音频特征..."



        # 3. 音频特征分析

        audio_features = analyze_audio_features(wav_path)



        # 4. 繁体→简体转换 + 关键词提取

        print("[PostProcess] 繁体转简体...")

        transcript["text"] = to_simplified(transcript.get("text", ""))

        for seg in transcript.get("segments", []):

            seg["text"] = to_simplified(seg.get("text", ""))



        print("[PostProcess] 提取关键词...")

        keywords = extract_keywords(transcript.get("text", ""))



        jobs[job_id]["progress"] = 90

        jobs[job_id]["detail"] = "正在后处理（繁简转换、关键词提取）..."



        # 5. 清理临时 WAV

        try:

            os.remove(wav_path)

        except:

            pass



        jobs[job_id]["result"] = {**transcript, "audio_features": audio_features, "keywords": keywords}

        jobs[job_id]["status"] = "done"

        jobs[job_id]["progress"] = 100

        jobs[job_id]["detail"] = "转写完成"



    except Exception as e:
        import traceback, datetime
        tb = traceback.format_exc()
        traceback.print_exc()
        # 把完整堆栈写入 debug 日志，便于事后定位（日志位于系统 temp/video_analyzer/）
        try:
            with open(str(TEMP_DIR / 'transcribe_debug.log'), 'a', encoding='utf-8') as f:
                f.write(f"\n[{datetime.datetime.now()}] JOB {job_id} FAILED\n{tb}\n")
        except Exception:
            pass

        jobs[job_id]["status"] = "error"

        msg = str(e)
        low = msg.lower()
        # 把底层 libsndfile / 系统错误翻译成用户可懂的提示
        if "errno 22" in low or "invalid argument" in low or "format not recognised" in low or "not recognised" in low:
            msg = "音频解码失败（可能是音频格式不支持，或视频无有效音轨/为静音视频）"
        jobs[job_id]["error"] = msg

        jobs[job_id]["progress"] = 100



# ── API 路由 ──



@app.route("/api/transcribe", methods=["POST"])

def api_transcribe():

    if "video" not in request.files:

        return jsonify({"error": "缺少 video 文件"}), 400



    video_file = request.files["video"]

    duration = float(request.form.get("duration", 60))

    # 模型选择（前端传来的 model 参数）

    model_name = request.form.get("model", "").strip().lower()

    if model_name not in [m[0] for m in WHISPER_MODEL_CHOICES]:

        model_name = _whisper_model_name  # 默认

    print(f"[Transcribe] 使用模型: {model_name}")



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



    jobs[job_id] = {

        "status": "starting",

        "progress": 0,

        "detail": "任务已创建，等待处理...",

        "result": None,

        "error": None,

        "video_path": video_path,

        "duration": duration,

        "filename": video_file.filename,

        "current_chunk": "",

        "start_time": time.time(),

    }



    thread = threading.Thread(target=run_transcription, args=(job_id, video_path, duration, model_name), daemon=True)

    thread.start()



    return jsonify({

        "job_id": job_id,

        "status": "starting",

        "message": f"任务已创建，{video_file.filename} 正在转写中...",

        "model": model_name,

    })



@app.route("/api/whisper-models", methods=["GET"])

def api_whisper_models():

    """返回可用的 Whisper 模型列表"""

    return jsonify({

        "models": WHISPER_MODEL_CHOICES,

        "default": _whisper_model_name,

        "cached": list(set(k.split("#")[0] for k in _whisper_models.keys())),

    })



@app.route("/api/status/<job_id>")

def api_status(job_id):

    job = jobs.get(job_id)

    if not job:

        return jsonify({"error": "任务不存在"}), 404

    resp = {

        "job_id": job_id,

        "status": job["status"],

        "progress": job["progress"],

        "detail": job.get("detail", ""),

        "error": job.get("error"),

    }

    # 计算已用时间
    start_t = job.get("start_time")
    if start_t:
        resp["elapsed_sec"] = round(time.time() - start_t, 1)

    if job["status"] == "transcribing":

        resp["current_chunk"] = job.get("current_chunk", "")

    return jsonify(resp)



@app.route("/api/result/<job_id>")

def api_result(job_id):

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



# ── 导出保存端点（保存到项目 exports 目录，而非浏览器 Downloads）──

@app.route("/api/save-export", methods=["POST"])

def api_save_export():

    import shutil

    folder_name = request.form.get("folder_name", "").strip()

    if not folder_name:

        return jsonify({"error": "缺少 folder_name 参数"}), 400

    # 安全：禁止路径穿越
    folder_name = folder_name.replace("..", "").replace("/", "_").replace("\\", "_")

    export_path = EXPORT_DIR / folder_name

    if export_path.exists():

        shutil.rmtree(export_path, ignore_errors=True)

    # 创建子目录结构
    html_dir = export_path / "html"
    md_dir = export_path / "markdown"
    pic_dir = export_path / "pic"
    html_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)
    pic_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []

    # 保存 HTML
    if "html" in request.files:
        fname = request.files["html"].filename or f"{folder_name}.html"
        fpath = html_dir / fname
        request.files["html"].save(str(fpath))
        saved_files.append(f"html/{fname}")

    # 保存 CSS
    if "css" in request.files:
        fname = request.files["css"].filename or "report_style.css"
        fpath = html_dir / fname
        request.files["css"].save(str(fpath))
        saved_files.append(f"html/{fname}")

    # 保存 Markdown
    if "markdown" in request.files:
        fname = request.files["markdown"].filename or f"{folder_name}.md"
        fpath = md_dir / fname
        request.files["markdown"].save(str(fpath))
        saved_files.append(f"markdown/{fname}")

    # 保存 PNG
    if "png" in request.files:
        fname = request.files["png"].filename or f"{folder_name}.png"
        fpath = pic_dir / fname
        request.files["png"].save(str(fpath))
        saved_files.append(f"pic/{fname}")

    print(f"[Export] 保存到 {export_path} ({len(saved_files)} 个文件)")

    return jsonify({
        "status": "ok",
        "path": str(export_path),
        "files": saved_files,
    })



@app.route("/api/video-meta", methods=["GET", "POST"])

def api_video_meta():

    # GET: 健康检查

    if request.method == "GET":

        return jsonify({"status": "ok", "model": "small", "version": "1.0"})

    

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

            probe_cmd = f'{_quote(get_ffmpeg())} -i {_quote(video_path)} -hide_banner'

            pr = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='replace', shell=True)

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



# ============================================================
# 文案深度分析端点（需要 LLM API Key）
# ============================================================


def call_llm_analyze(input_data_str, api_key=None, base_url=None, model_name=None,
                     provider=None, ollama_base=None):
    import requests
    provider = (provider or "").strip().lower()
    # 前端传入的 key 优先，否则读环境变量
    api_key = api_key or os.environ.get("LLM_API_KEY", "")
    base_url = base_url or os.environ.get("LLM_BASE_URL", "")
    if not api_key and provider != "ollama":
        return {"error": "请先填入 API Key", "available": False}
    # 服务商判定：显式 provider 优先，否则按 key 前缀自动检测
    is_siliconflow = (provider == "siliconflow") or (
        not provider and ("siliconflow" in base_url.lower()
                          or (not base_url and len(api_key) > 30 and api_key.startswith("sk-")))
    )
    is_deepseek = (provider == "deepseek") or (
        not provider and "deepseek" in base_url.lower()
    )
    if is_siliconflow:
        base_url = "https://api.siliconflow.cn/v1/chat/completions"
    elif is_deepseek:
        base_url = "https://api.deepseek.com/v1/chat/completions"
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
        base = _normalize_ollama_base(
            ollama_base or os.environ.get("OLLAMA_BASE", "http://localhost:11434")
        )
        model = model_name or os.environ.get("LLM_MODEL", "llama3.1")
        try:
            resp = requests.post(base + "/api/chat", json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                # 顶层 think:false 关闭思考模式（Qwen3.5 等带 thinking 的模型，
                # 否则会先输出大量思考过程，导致正式内容为空或极短）
                "think": False,
                # num_predict=8192：九节带货报告含大量表格，通常需 6000-8000 token，
                # 4096 会导致生成到中途（约第四节）被截断
                "options": {"temperature": 0.3, "num_predict": 8192},
            }, timeout=300)
            if resp.status_code == 200:
                odata = resp.json()
                content = odata.get("message", {}).get("content", "") or ""
                # 兜底：部分带思考模式的模型 content 为空但 thinking 有内容
                if not content.strip():
                    content = odata.get("message", {}).get("thinking", "") or ""
                    # thinking 通常以 "Thinking Process:..." 开头，去掉思考前缀取正式回答
                    idx = content.find("最终回答")
                    if idx == -1:
                        idx = content.find("Final Answer")
                    if idx == -1:
                        idx = content.find("<｜end▁of▁thinking｜>")
                    if idx != -1:
                        content = content[idx:]
                return {"report": content, "available": True, "model": model}
            return {"error": "Ollama HTTP " + str(resp.status_code) + ": " + resp.text[:300],
                    "available": True, "model": model}
        except Exception as e:
            return {"error": "Ollama 连接失败（" + base + "）：" + str(e), "available": True}
    # SiliconFlow 默认用 Qwen2.5-72B，DeepSeek 默认 deepseek-chat，智谱默认 glm-4-flash
    if is_siliconflow:
        model = model_name or os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")
    elif is_deepseek:
        model = model_name or os.environ.get("LLM_MODEL", "deepseek-chat")
    else:
        model = model_name or os.environ.get("LLM_MODEL", "glm-4-flash")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        # max_tokens=12000：九节带货报告含大量表格，需较大生成预算
        "max_tokens": 12000,
    }
    try:
        resp = requests.post(
            base_url,
            headers=headers_dict, json=payload, timeout=600,
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


def run_analysis(job_id, input_data, api_key, provider, ollama_base, model_name):
    """后台线程：调用 LLM 进行深度分析"""
    try:
        analyze_jobs[job_id]["status"] = "analyzing"
        analyze_jobs[job_id]["progress"] = 30
        result = call_llm_analyze(
            input_data,
            api_key=api_key,
            provider=provider,
            ollama_base=ollama_base,
            model_name=model_name,
        )
        analyze_jobs[job_id]["result"] = result
        analyze_jobs[job_id]["model"] = result.get("model", None)
        if result.get("error"):
            analyze_jobs[job_id]["status"] = "error"
            analyze_jobs[job_id]["error"] = result["error"]
        else:
            analyze_jobs[job_id]["status"] = "done"
        analyze_jobs[job_id]["progress"] = 100
    except Exception as e:
        import traceback
        traceback.print_exc()
        analyze_jobs[job_id]["status"] = "error"
        analyze_jobs[job_id]["error"] = str(e)
        analyze_jobs[job_id]["progress"] = 100


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

    frames = analysis.get("frames", [])

    frame_summary = []

    for f in frames[:20]:

        frame_summary.append(

            f"- {f.get('t',0):.1f}s | 亮度:{round(f.get('brightness',0),3)} "

            f"| 主色:{f.get('dominantColor','N/A')} | 景别:{f.get('shotType','N/A')} "

            f"| 字幕:{'有' if f.get('textRatio',0)>5 else '无'} "

            f"| 人物:{'有' if f.get('skinRatio',0)>0.05 else '无'}"

        )

    kw = transcription.get("keywords", {}) or {}

    input_data = (

        "【视频基本信息】\n"

        f"- 文件名：{analysis.get('name','未知')}\n"

        f"- 时长：{analysis.get('duration',0):.1f}秒\n"

        f"- 分辨率：{video_meta.get('width',0)}x{video_meta.get('height',0)}\n"

        f"- 帧数：{len(frames)} 帧\n\n"

        "【逐字稿（按时间分段）】\n"

        + seg_text +

        "\n\n【帧画面摘要（前20帧）】\n"

        + "\n".join(frame_summary) +

        "\n\n【关键词】\n"

        f"高频词：{kw.get('highFreq',[])[:20]}\n"

        f"动作词：{kw.get('actions',[])[:10]}\n"

        f"情绪词：{kw.get('emotions',[])[:10]}\n"

    )

    job_id = str(uuid.uuid4())[:8]
    analyze_jobs[job_id] = {
        "status": "starting",
        "progress": 5,
        "result": None,
        "error": None,
        "model": None,
    }

    thread = threading.Thread(
        target=run_analysis,
        args=(job_id, input_data, api_key, provider, ollama_base, body.get("model") or None),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "starting",
        "message": "分析任务已创建，正在生成中...",
    })


@app.route("/api/analyze-status/<job_id>")
def api_analyze_status(job_id):
    job = analyze_jobs.get(job_id)
    if not job:
        return jsonify({"error": "分析任务不存在"}), 404
    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "error": job.get("error"),
    })


@app.route("/api/analyze-result/<job_id>")
def api_analyze_result(job_id):
    job = analyze_jobs.get(job_id)
    if not job:
        return jsonify({"error": "分析任务不存在"}), 404
    result = job.get("result") or {}
    return jsonify({
        "status": job["status"],
        "has_llm": result.get("available", False),
        "report": result.get("report", None),
        "result": result,  # 嵌套结构，兼容前端 rData.result.report 读取
        "error": result.get("error", None) or job.get("error"),
        "model": job.get("model") or result.get("model", None),
    })


# ── API Key 验证端点 ──
def _normalize_ollama_base(base):
    """规范化 Ollama 地址：强制 IPv4 直连（Ollama 默认只监听 127.0.0.1，
    localhost 在部分系统会优先解析为 ::1 导致连接被拒）"""
    base = (base or "http://localhost:11434").strip().rstrip("/")
    if "localhost" in base.lower():
        base = base.lower().replace("localhost", "127.0.0.1")
    return base


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
    ollama_base = _normalize_ollama_base(
        body.get("ollama_base") or os.environ.get("OLLAMA_BASE", "http://localhost:11434")
    )

    # ── Ollama 本地模型（无需 API Key） ──
    if provider == "ollama":
        try:
            resp = _req.get(ollama_base + "/api/tags", timeout=10)
            if resp.status_code == 200:
                mlist = resp.json().get("models", [])
                models = []
                for m in mlist:
                    name = m.get("name") or m.get("model") or ""
                    if name:
                        models.append({"id": name, "name": name})
                if not models:
                    return jsonify({
                        "ok": False,
                        "error": "Ollama 已连接（" + ollama_base + "），但本地没有模型。请用 `ollama pull <模型名>` 拉取，例如：ollama pull llama3.1",
                        "available_models": [],
                    })
                return jsonify({
                    "ok": True,
                    "model": models[0]["id"],
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
            import traceback
            traceback.print_exc()
            return jsonify({
                "ok": False,
                "error": "无法连接 Ollama（" + ollama_base + "）：" + repr(e) + "。请确认 Ollama 已启动。",
                "available_models": [],
            })

    if not api_key:
        return jsonify({"ok": False, "error": "API Key 不能为空"})

    # 服务商判定：显式 provider 优先，否则按 key 前缀自动检测
    is_sf = (provider == "siliconflow") or (not provider and api_key.startswith("sk-"))
    is_ds = (provider == "deepseek")
    if is_sf:
        base_url = "https://api.siliconflow.cn/v1/chat/completions"
        models = [
            {"id": "Qwen/Qwen2.5-72B-Instruct",  "name": "Qwen2.5-72B（推荐·效果最好）"},
            {"id": "deepseek-ai/DeepSeek-V2.5",  "name": "DeepSeek V2.5（性价比）"},
            {"id": "deepseek-ai/DeepSeek-V3",    "name": "DeepSeek V3"},
            {"id": "Qwen/Qwen2.5-14B-Instruct",  "name": "Qwen2.5-14B"},
            {"id": "Qwen/Qwen2.5-7B-Instruct",   "name": "Qwen2.5-7B（速度快）"},
            {"id": "THUDM/glm-4-9b-chat",        "name": "GLM-4-9B"},
            {"id": "iic/llama3.1-8b-instruct",   "name": "Llama3.1-8B"},
            {"id": "iic/qwen2-7b-instruct",      "name": "Qwen2-7B"},
        ]
        default_model = "Qwen/Qwen2.5-72B-Instruct"
    elif is_ds:
        base_url = "https://api.deepseek.com/v1/chat/completions"
        models = [
            {"id": "deepseek-chat",     "name": "DeepSeek-V3.2（推荐·快且强）"},
            {"id": "deepseek-reasoner", "name": "DeepSeek-R1（深度推理·较慢）"},
        ]
        default_model = "deepseek-chat"
    else:
        base_url = os.environ.get(
            "LLM_BASE_URL",
            "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        )
        models = [
            {"id": "glm-4-flash",  "name": "GLM-4-Flash（默认·推荐）"},
            {"id": "glm-4",        "name": "GLM-4"},
            {"id": "glm-4-plus",   "name": "GLM-4-Plus"},
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
                "provider": "SiliconFlow" if is_sf else ("DeepSeek" if is_ds else "Zhipu/Other"),
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

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Video Content Analyzer Backend")

    parser.add_argument("--host", default="0.0.0.0", help="监听地址")

    parser.add_argument("--port", type=int, default=8766, help="监听端口")

    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium"], help="Whisper 模型")
    args = parser.parse_args()
    _whisper_model_name = args.model


    print(f"""

╔══════════════════════════════════════════════════════════════╗

║   Video Content Analyzer Backend                              ║

║   转写服务  http://{args.host}:{args.port}                        ║

║   转写模式  并行分片（ThreadPool + 多模型实例池）      ║

╚══════════════════════════════════════════════════════════════╝

  Whisper 模型 : {args.model}（前端可选 tiny/base/small/medium）

  音频格式     : WAV 16kHz 单声道（soundfile 直读，不调 ffmpeg）

  分片大小     : {CHUNK_SECONDS} 秒/段

  并行度       : tiny/base=3线程, small=2线程, medium=1线程

  依赖         : imageio-ffmpeg（音频提取）+ soundfile（Whisper 输入）

""")

    # Print LAN access URL

    if args.host == '0.0.0.0':

        import socket

        try:

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            s.connect(('8.8.8.8', 1))

            ip = s.getsockname()[0]

            print(f'  LAN access: http://{ip}:{args.port}')

        except Exception:

            pass

        finally:

            s.close() if 's' in dir() else None

    

    app.run(host=args.host, port=args.port, debug=False, threaded=True)



