"""

Video Content Analyzer - Python Backend

功能：音频提取 + Qwen3-ASR-1.7B 语音转写（本地大模型，GPU DirectML+Vulkan）

依赖：imageio-ffmpeg / flask / soundfile / numpy / onnxruntime-directml

启动：python transcribe_server.py

接口：POST /api/transcribe        上传视频，开始转写

      GET  /api/status/<job_id>  查询任务状态（含真实进度）

      GET  /api/result/<job_id>  获取转写结果

      GET  /api/video-meta       视频元数据

"""

import os

# 必须在导入 onnxruntime/torch 之前设置：
# Qwen3-ASR 的 onnxruntime 带 libiomp5md.dll，与 torch 的 libomp140 冲突会导致
# OMP Error #15 进程崩溃。此环境变量允许重复加载 OpenMP 运行时。
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import uuid

import json

import sys

import threading

import subprocess

import tempfile

import time

from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from flask_cors import CORS

import zhconv  # 繁体→简体转换

import db  # SQLite 持久化层（任务/分析结果落盘，重启不丢）



# ── 懒加载 ──

_ffmpeg_exe = None
_qwen3_asr_gguf_engine = None  # Qwen3-ASR GGUF 引擎实例（懒加载）
_qwen3_asr_lock = threading.Lock()  # Qwen3-ASR 引擎初始化锁

# 并发转写信号量：Qwen3-ASR 引擎实例较重，强制串行（一次一个转写任务）
MAX_CONCURRENT_TRANSCRIBE = 1
_transcribe_semaphore = threading.Semaphore(MAX_CONCURRENT_TRANSCRIBE)



def get_ffmpeg():

    """获取 imageio-ffmpeg 自带的 ffmpeg 路径（用于音频提取）"""

    global _ffmpeg_exe

    if _ffmpeg_exe is None:

        try:

            import imageio_ffmpeg

            _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

            print(f"[FFmpeg] 使用 imageio-ffmpeg: {_ffmpeg_exe}")

        except ImportError:

            _ffmpeg_exe = "ffmpeg"

    return _ffmpeg_exe







# ── 任务存储 ──

# 持久化：任务/结果写入 SQLite（backend/data/analyzer.db），重启后自动恢复
db.init_db()

jobs = {}  # job_id -> {status, progress, result, error, current_chunk, ...}
analyze_jobs = {}  # job_id -> {status, progress, result, error, model}

# 启动时从数据库恢复已完成任务（重启不丢历史）
_jobs_restored = db.load_transcribe_jobs()
if _jobs_restored:
    jobs.update(_jobs_restored)
    print(f"[DB] 已恢复 {len(_jobs_restored)} 个转写任务")

_analyze_jobs_restored = db.load_analyze_jobs()
if _analyze_jobs_restored:
    analyze_jobs.update(_analyze_jobs_restored)
    print(f"[DB] 已恢复 {len(_analyze_jobs_restored)} 个文案分析任务")


def _persist_job(job_id):
    """把内存中的转写任务状态同步写入数据库（任务创建/状态变更/完成时调用）"""
    job = jobs.get(job_id)
    if job:
        try:
            db.save_transcribe_job(job_id, job)
        except Exception as e:
            print(f"[DB] 转写任务持久化失败 {job_id}: {e}")


def _persist_analyze_job(job_id):
    """把内存中的文案分析任务状态同步写入数据库"""
    job = analyze_jobs.get(job_id)
    if job:
        try:
            db.save_analyze_job(job_id, job)
        except Exception as e:
            print(f"[DB] 文案分析持久化失败 {job_id}: {e}")

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

def run_audio_extract(job_id: str, video_path: str, duration: float):
    """上传后第一步：仅提取音频，不自动转写。提取完成状态置为 audio_ready，
    由前端选择识别引擎（Whisper / Qwen3-ASR）后调用 /api/transcribe-start 启动转写。"""
    try:
        jobs[job_id]["status"] = "extracting"
        jobs[job_id]["progress"] = 8
        jobs[job_id]["detail"] = "正在提取音频..."

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
            _persist_job(job_id)  # 落库
            return

        # 音频就绪，等待用户选择模型
        jobs[job_id]["status"] = "audio_ready"
        jobs[job_id]["progress"] = 20
        jobs[job_id]["detail"] = "音频提取完成，请选择识别模型开始转写"
        jobs[job_id]["wav_path"] = wav_path
        _persist_job(job_id)  # 落库
        print(f"[Audio] job {job_id} 音频就绪: {wav_path}", flush=True)

    except Exception as e:
        import traceback, datetime
        traceback.print_exc()
        try:
            with open(str(TEMP_DIR / 'transcribe_debug.log'), 'a', encoding='utf-8') as f:
                f.write(f"\n[{datetime.datetime.now()}] JOB {job_id} AUDIO_EXTRACT FAILED\n{traceback.format_exc()}\n")
        except Exception:
            pass
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["progress"] = 100
        _persist_job(job_id)  # 落库


def run_transcribe_with_engine(job_id: str, engine: str = "qwen3_asr", model_name: str = None):
    """用户选择识别引擎后启动转写。当前仅支持 Qwen3-ASR（Whisper 已移除）。"""

    # 并发限制：Whisper 多实例并发不安全，强制串行（Qwen3-ASR 同样串行避免显存竞争）
    if _transcribe_semaphore.acquire(blocking=False):
        pass
    else:
        jobs[job_id]["status"] = "waiting"
        jobs[job_id]["progress"] = 2
        jobs[job_id]["detail"] = "前面有转写任务进行中，正在排队等待..."
        print(f"[Queue] job {job_id} 排队等待转写槽位...", flush=True)
        _transcribe_semaphore.acquire()

    try:
        job = jobs.get(job_id)
        if not job:
            return
        wav_path = job.get("wav_path") or str(TEMP_DIR / f"{job_id}.wav")
        duration = job.get("duration", 60.0)
        video_path = job.get("video_path", "")

        if engine != "qwen3_asr":
            engine = "qwen3_asr"  # Whisper 已移除，强制使用 Qwen3-ASR
        jobs[job_id]["status"] = "transcribing"
        jobs[job_id]["progress"] = 15
        jobs[job_id]["detail"] = "正在加载 Qwen3-ASR 模型..."
        transcript = transcribe_qwen3_asr(wav_path, job_id, model_name=model_name)

        jobs[job_id]["status"] = "analyzing"
        jobs[job_id]["progress"] = 80
        jobs[job_id]["detail"] = "转写完成，正在分析音频特征..."

        # 音频特征分析
        audio_features = analyze_audio_features(wav_path)

        # 繁体→简体转换 + 关键词提取
        print("[PostProcess] 繁体转简体...")
        transcript["text"] = to_simplified(transcript.get("text", ""))
        for seg in transcript.get("segments", []):
            seg["text"] = to_simplified(seg.get("text", ""))

        print("[PostProcess] 提取关键词...")
        keywords = extract_keywords(transcript.get("text", ""))

        jobs[job_id]["progress"] = 90
        jobs[job_id]["detail"] = "正在后处理（繁简转换、关键词提取）..."

        # 清理临时 WAV（视频文件保留：P0 钩子/BGM/卡点分析需要，由启动时定时清理旧文件）
        try:
            os.remove(wav_path)
        except:
            pass

        jobs[job_id]["result"] = {**transcript, "audio_features": audio_features, "keywords": keywords, "engine": engine}
        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["detail"] = "转写完成"
        jobs[job_id]["finished_at"] = time.time()
        _persist_job(job_id)  # 落库：完成状态 + 结果

    except Exception as e:
        import traceback, datetime
        tb = traceback.format_exc()
        traceback.print_exc()
        try:
            with open(str(TEMP_DIR / 'transcribe_debug.log'), 'a', encoding='utf-8') as f:
                f.write(f"\n[{datetime.datetime.now()}] JOB {job_id} FAILED\n{tb}\n")
        except Exception:
            pass
        jobs[job_id]["status"] = "error"
        msg = str(e)
        low = msg.lower()
        if "errno 22" in low or "invalid argument" in low or "format not recognised" in low or "not recognised" in low:
            msg = "音频解码失败（可能是音频格式不支持，或视频无有效音轨/为静音视频）"
        jobs[job_id]["error"] = msg
        jobs[job_id]["progress"] = 100
        jobs[job_id]["finished_at"] = time.time()
        _persist_job(job_id)  # 落库：错误状态

    finally:
        _transcribe_semaphore.release()


class _JobStreamTee:
    """把引擎打印到 stdout 的逐词输出累积进 job 状态，供 /api/status 实时暴露。

    背景：引擎 `_decode(streaming=True)`（默认开）会**逐 token** 把解码结果
    `print(..., end='')` 到 stdout，标点后自动补换行 —— 也就是 stdout 上本来就有
    一路实时文本流。但服务端 stdout 是否被重定向到文件**不可控**（自动拉起 /
    以服务方式启动时可能指向控制台，实测就抓不到），所以不依赖日志文件，
    而是在转写期间把 sys.stdout 换成这个 tee：既照常写原 stdout（保留既有日志行为），
    又把内容累积进 `jobs[job_id]["current_chunk"]`。

    不改第三方引擎代码；`print` 在调用时才解析 sys.stdout，所以替换立即生效。
    """

    _STOP = "📊 性能统计"      # 引擎收尾会打印统计块 → 到此冻结，别把统计混进正文

    def __init__(self, job_id, real):
        self.job_id = job_id
        self.real = real
        self.frozen = False
        self.buf = []
        j = jobs.get(job_id)
        if j is not None:
            j["current_chunk"] = ""
            j["chunk_chars"] = 0

    def write(self, s):
        if not s:
            return 0
        if not self.frozen:
            self.buf.append(s)
            blob = "".join(self.buf)
            if self._STOP in blob:
                blob = blob.split(self._STOP, 1)[0]
                self.frozen = True
            j = jobs.get(self.job_id)
            if j is not None:
                j["current_chunk"] = blob
                j["chunk_chars"] = len(blob)
        try:
            self.real.write(s)
        except Exception:
            pass
        return len(s)

    def flush(self):
        try:
            self.real.flush()
        except Exception:
            pass

    def isatty(self):
        return False


def transcribe_qwen3_asr(wav_path: str, job_id: str, model_name: str = None):
    """使用 Qwen3-ASR-GGUF 本地引擎转写（ONNX Encoder + GGUF Decoder, DirectML/Vulkan 加速）。

    输出带时间戳的分段（来自 Qwen3-ForcedAligner 字级对齐），结构与 Whisper 一致：
    {"text": 全文, "segments": [{"start", "end", "text"}]}
    """
    global _qwen3_asr_gguf_engine

    # 模型目录：backend/qwen3_asr_models/（GGUF/ONNX 模型文件所在根目录）
    model_dir = os.environ.get("QWEN3_ASR_MODEL_DIR") or str(Path(__file__).parent / "qwen3_asr_models")
    gguf_src = str(Path(__file__).parent / "qwen3_asr_gguf_src")

    # 懒加载引擎
    if _qwen3_asr_gguf_engine is None:
        with _qwen3_asr_lock:
            if _qwen3_asr_gguf_engine is None:
                print(f"[Qwen3-ASR] 初始化 GGUF 引擎（模型目录: {model_dir}）...", flush=True)
                t0 = time.time()
                # 注意：这里**不要**再 `import sys` —— 那会让 sys 变成本函数的局部变量，
                # 而本函数后面要用 sys.stdout 做流式 tee；引擎已初始化时这句不执行，
                # 就会抛 UnboundLocalError。模块顶层已 import sys，直接用即可。
                if gguf_src not in sys.path:
                    sys.path.insert(0, gguf_src)
                from qwen_asr_gguf.inference import QwenASREngine, ASREngineConfig, AlignerConfig

                config = ASREngineConfig(
                    model_dir=model_dir,
                    onnx_provider='DML',
                    llm_use_gpu=True,
                    # 🔧 n_ctx 2048→4096：消除长视频 KV 缓存溢出导致的 GGML_ASSERT 硬崩溃
                    #    （n_ctx=2048 + memory_chunks=1 时部分长片 token 数逼近上限，解码越界）。
                    n_ctx=4096,
                    enable_aligner=True,
                    # 显式指定与下载文件匹配的文件名（int4/q4_k 量化版）
                    encoder_frontend_fn='qwen3_asr_encoder_frontend.int4.onnx',
                    encoder_backend_fn='qwen3_asr_encoder_backend.int4.onnx',
                    llm_fn='qwen3_asr_llm.q4_k.gguf',
                    align_config=AlignerConfig(
                        onnx_provider='DML',
                        llm_use_gpu=True,
                        # 🔧 与 ASR 解码器保持一致，避免 Aligner 侧同样溢出
                        n_ctx=4096,
                        model_dir=model_dir,
                        encoder_frontend_fn='qwen3_aligner_encoder_frontend.int4.onnx',
                        encoder_backend_fn='qwen3_aligner_encoder_backend.int4.onnx',
                        llm_fn='qwen3_aligner_llm.q4_k.gguf',
                    )
                )
                _qwen3_asr_gguf_engine = QwenASREngine(config=config)
                print(f"[Qwen3-ASR] 引擎初始化完成（耗时 {time.time()-t0:.1f}s）", flush=True)

    print(f"[Qwen3-ASR] 转写中: {wav_path}", flush=True)
    jobs[job_id]["detail"] = "Qwen3-ASR 识别中..."
    # 用 load_audio 加载音频数组后直接传给 asr（audio_file 方式在部分环境读取异常）
    import numpy as np
    from qwen_asr_gguf.inference.audio import load_audio
    audio = load_audio(wav_path, sample_rate=16000)

    # 上下文提示（热词引导）：注入内容类型/领域词，显著降低同音字错误。
    # 例：识别"夹子音"时，context 含"直播带货"可引导模型偏向该领域词汇。
    # 可通过环境变量 QWEN3_ASR_CONTEXT 自定义（默认通用直播带货场景）。
    qwen_context = os.environ.get(
        "QWEN3_ASR_CONTEXT",
        "这是中文短视频直播带货内容。注意识别网络用语和口语，"
        "例如\"夹子音\"\"破价\"\"家人们\"\"闭眼入\"等，避免同音字误写。"
    )
    # 采样温度：默认 0.4 → 0.3 更保守，减少同音字发散。
    # 实测：0.2 对个别词过保守（半甜→半田），0.3 平衡准确与自然。
    # 可经 QWEN3_ASR_TEMPERATURE 环境变量调。
    try:
        qwen_temp = float(os.environ.get("QWEN3_ASR_TEMPERATURE", "0.3"))
    except ValueError:
        qwen_temp = 0.3

    # ⚠️ memory_chunks 必须与 n_ctx 匹配，否则 KV 缓存溢出：
    #    n_ctx=4096（已上调），chunk=40s≈800 token；memory_chunks=1 → 800+800=1600 ✅ 余量充足
    #    memory_chunks=2 → 800+1600=2400 < 4096 ✅ 亦安全（原 n_ctx=2048 时 2400>2048 才崩）。
    #    （引擎 schema.py 文档化的安全值即 memory_num=1；此处 n_ctx 在服务端显式覆盖为 4096。）
    # 逐词流式输出：把引擎 stdout 的 token 流同时累积进 job 状态（见 _JobStreamTee）
    _tee = _JobStreamTee(job_id, sys.stdout)
    _old_stdout = sys.stdout
    sys.stdout = _tee
    try:
        res = _qwen3_asr_gguf_engine.asr(
            audio=audio,
            context=qwen_context,
            language="Chinese",
            chunk_size_sec=40.0,
            memory_chunks=1,
            temperature=qwen_temp,
        )
    finally:
        sys.stdout = _old_stdout

    full_text = res.text or ""
    segments = []
    if res.alignment and len(res.alignment.items) > 0:
        # 字级时间戳聚合为句子级分段
        cur_text = ""
        cur_start = None
        cur_end = None
        for it in res.alignment.items:
            t = (it.text or "").strip()
            if not t:
                continue
            if cur_start is None:
                cur_start = it.start_time
            cur_end = it.end_time
            cur_text += t
            if t.endswith(("。", "！", "？", ".", "!", "?")) or (it.end_time - it.start_time > 1.5):
                segments.append({"start": round(cur_start, 2), "end": round(cur_end, 2), "text": cur_text})
                cur_text = ""
                cur_start = None
        if cur_text:
            segments.append({"start": round(cur_start or 0, 2), "end": round(cur_end or 0, 2), "text": cur_text})
    if not segments and full_text:
        # 无对齐时间戳时整段兜底
        import soundfile as sf
        data, sr = sf.read(wav_path)
        segments = [{"start": 0.0, "end": round(len(data) / sr, 2), "text": full_text}]

    print(f"[Qwen3-ASR] 完成: {len(segments)} 段, 文本长度 {len(full_text)}", flush=True)
    return {"text": full_text, "segments": segments, "engine": "qwen3_asr"}


# ── API 路由 ──



@app.route("/api/transcribe", methods=["POST"])

def api_transcribe():

    if "video" not in request.files:

        return jsonify({"error": "缺少 video 文件"}), 400



    video_file = request.files["video"]

    # duration 异常保护：非法值（非数值/<=0/NaN）回退默认 60 秒，避免 float() 抛 ValueError → 500
    try:
        duration = float(request.form.get("duration", 60))
        if duration != duration or duration <= 0 or duration > 36000:  # NaN 自比较 / 上限 10h
            duration = 60.0
    except (TypeError, ValueError):
        duration = 60.0

    # 模型选择（兼容旧前端传参，固定 Qwen3-ASR）
    model_name = request.form.get("model", "").strip().lower() or "Qwen/Qwen3-ASR-1.7B"

    print(f"[Transcribe] 使用引擎: Qwen3-ASR ({model_name})")



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

    _persist_job(job_id)  # 落库：任务创建即持久化，重启不丢



    # 上传后先只提取音频（不自动转写），提取完成状态变为 audio_ready，
    # 由前端选择识别引擎（Whisper / Qwen3-ASR）后再调用 /api/transcribe-start 启动转写
    thread = threading.Thread(target=run_audio_extract, args=(job_id, video_path, duration), daemon=True)
    thread.start()



    return jsonify({

        "job_id": job_id,

        "status": "starting",

        "message": f"任务已创建，{video_file.filename} 音频提取中，提取完成后可选择识别模型开始转写",

        "model": model_name,

    })



@app.route("/api/transcribe-start", methods=["POST"])

def api_transcribe_start():

    """启动 Qwen3-ASR 转写（Whisper 已移除，engine 参数仅兼容旧前端）"""

    try:
        body = request.get_json() or {}
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    job_id = (body.get("job_id") or "").strip()
    engine = (body.get("engine") or "qwen3_asr").strip().lower()
    model = (body.get("model") or "").strip() or None

    if not job_id or job_id not in jobs:
        return jsonify({"error": "任务不存在"}), 404

    job = jobs[job_id]
    if job.get("status") in ("transcribing", "analyzing", "done", "waiting"):
        return jsonify({"error": f"任务当前状态为 {job.get('status')}，无法重复启动"}), 400

    if engine != "qwen3_asr":
        engine = "qwen3_asr"  # Whisper 已移除，强制 Qwen3-ASR

    print(f"[Transcribe-Start] job {job_id} 启动转写 engine={engine} model={model or '默认'}", flush=True)
    thread = threading.Thread(target=run_transcribe_with_engine, args=(job_id, engine, model), daemon=True)
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "transcribing",
        "engine": engine,
        "message": f"已启动 {engine} 转写...",
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




    return jsonify({"job_id": job_id, "status": "done", "result": job["result"]})


# ── 历史记录查询（SQLite 持久化）──

@app.route("/api/history/transcribe", methods=["GET"])
def api_history_transcribe():
    """转写历史任务列表（持久化自 SQLite，重启不丢）"""
    try:
        limit = min(int(request.args.get("limit", 50)), 200)
    except (TypeError, ValueError):
        limit = 50
    items = db.query_transcribe_history(limit)
    return jsonify({"items": items, "total": len(items)})


@app.route("/api/history/transcribe/<job_id>", methods=["GET"])
def api_history_transcribe_detail(job_id):
    """转写历史任务详情（含完整结果）"""
    job = jobs.get(job_id) or db.load_transcribe_jobs().get(job_id)
    if not job:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify({"job_id": job_id, "status": "done", "result": job.get("result")})


@app.route("/api/history/analysis", methods=["GET"])
def api_history_analysis():
    """智能分析历史（钩子/OCR/信息密度/视觉锚点）"""
    job_id = (request.args.get("job_id") or "").strip() or None
    try:
        limit = min(int(request.args.get("limit", 100)), 300)
    except (TypeError, ValueError):
        limit = 100
    items = db.query_analysis_results(job_id, limit)
    return jsonify({"items": items, "total": len(items)})



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
                     provider=None, ollama_base=None, job_id=None):
    import requests, re
    provider = (provider or "").strip().lower()

    # ── 进度明细辅助：更新 analyze_jobs[job_id] 的 progress / detail ──
    def _set_progress(p, detail=None):
        if not job_id or job_id not in analyze_jobs:
            return
        analyze_jobs[job_id]["progress"] = max(
            analyze_jobs[job_id].get("progress", 0), min(100, int(p))
        )
        if detail:
            analyze_jobs[job_id]["detail"] = detail

    def _cn2int(s):
        """中文数字 → int，支持 一~九十九（报告节数足够）"""
        d = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"零":0}
        s = s.strip()
        if s.isdigit():
            return int(s)
        if "十" in s:
            parts = s.split("十")
            left = d.get(parts[0], 1) if parts[0] else 1
            right = d.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
            return left * 10 + right
        return d.get(s, 0)

    # 预估总节数（一句总结 + 八节正文 = 9），动态上调
    _total_sections = [9]
    _seen_sections = []
    _section_re = re.compile(r'(?:^|\n)###\s+(.+?)(?:\n|$)')
    _num_re = re.compile(r'第\s*([一二三四五六七八九十零\d]+)\s*节')

    def _update_chapter_progress(accumulated_text):
        for m in _section_re.finditer(accumulated_text):
            title = m.group(1).strip()
            if not title or title in _seen_sections:
                continue
            _seen_sections.append(title)
            nm = _num_re.search(title)
            if nm:
                n = _cn2int(nm.group(1))
                if n > _total_sections[0]:
                    _total_sections[0] = n
                p = 30 + (n / _total_sections[0]) * 60
                stage = f"第{nm.group(1)}节 · {title.split('·',1)[-1].strip()}"
            else:
                p = 30 + (len(_seen_sections) / _total_sections[0]) * 60
                stage = title
            _set_progress(p, "正在生成 · " + stage)
    _set_progress(30, "准备调用模型生成报告...")
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
        _think_re = re.compile(r"<think>.*?</think>", re.DOTALL)
        try:
            _set_progress(35, f"正在连接 Ollama · {model} ...")
            resp = requests.post(base + "/api/chat", json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": True,
                # 顶层 think:false 关闭思考模式（Qwen3.5 等带 thinking 的模型，
                # 否则会先输出大量思考过程，导致正式内容为空或极短）
                "think": False,
                # num_predict=8192：九节带货报告含大量表格，通常需 6000-8000 token，
                # 4096 会导致生成到中途（约第四节）被截断
                "options": {"temperature": 0.3, "num_predict": 8192},
            }, stream=True, timeout=300)
            if resp.status_code == 200:
                chunks = []
                received = 0
                for raw in resp.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    try:
                        chunk = json.loads(raw)
                    except Exception:
                        continue
                    if chunk.get("done"):
                        break
                    delta = chunk.get("message", {}).get("content", "") or ""
                    if not delta:
                        continue
                    # 兜底：过滤模型可能泄露的思考块
                    delta = _think_re.sub("", delta)
                    if not delta.strip():
                        continue
                    chunks.append(delta)
                    received += len(delta)
                    # 章节检测：仅在累计文本中出现新 ### 标题时更新进度
                    _update_chapter_progress("".join(chunks))
                    # 字符流兜底：长时间无新章节时按已接收字符数补位，避免进度卡死
                    est = 30 + min(received / 6000.0, 1.0) * 60
                    if est > analyze_jobs.get(job_id, {}).get("progress", 0):
                        _set_progress(est, analyze_jobs.get(job_id, {}).get("detail"))
                content = "".join(chunks)
                # 整体再清洗一次思考块
                content = _think_re.sub("", content).strip()
                _set_progress(95, "报告主体已完成，正在收尾...")
                if not content:
                    return {"error": "Ollama 返回内容为空（可能是模型未就绪或思考模式未关闭）",
                            "available": True, "model": model}
                return {"report": content, "available": True, "model": model}
            # 非 200：退回非流式兜底
            try:
                odata = resp.json()
                content = odata.get("message", {}).get("content", "") or ""
                if content:
                    return {"report": content, "available": True, "model": model}
            except Exception:
                pass
            return {"error": "Ollama HTTP " + str(resp.status_code) + ": " + (resp.text or "")[:300],
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
        analyze_jobs[job_id]["detail"] = "准备调用模型生成报告..."
        result = call_llm_analyze(
            input_data,
            api_key=api_key,
            provider=provider,
            ollama_base=ollama_base,
            model_name=model_name,
            job_id=job_id,
        )
        analyze_jobs[job_id]["result"] = result
        analyze_jobs[job_id]["model"] = result.get("model", None)
        if result.get("error"):
            analyze_jobs[job_id]["status"] = "error"
            analyze_jobs[job_id]["error"] = result["error"]
        else:
            analyze_jobs[job_id]["status"] = "done"
        analyze_jobs[job_id]["progress"] = 100
        analyze_jobs[job_id]["finished_at"] = time.time()
        _persist_analyze_job(job_id)  # 落库：完成/错误状态 + 结果
    except Exception as e:
        import traceback
        traceback.print_exc()
        analyze_jobs[job_id]["status"] = "error"
        analyze_jobs[job_id]["error"] = str(e)
        analyze_jobs[job_id]["progress"] = 100
        analyze_jobs[job_id]["finished_at"] = time.time()
        _persist_analyze_job(job_id)  # 落库


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
        "start_time": time.time(),
    }
    _persist_analyze_job(job_id)  # 落库：任务创建即持久化

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
        "detail": job.get("detail", ""),
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



# ── P0 升级功能：钩子/BGM/卡点/算法评分 ──
# 由 media_analysis 模块提供实现（延迟 import，缺依赖时返回错误而非崩溃）

def _resolve_video(job_id=None, video_path=None):
    """解析视频文件路径：优先 job_id，其次显式 video_path。

    返回 (video_path, error)。error 为 None 表示成功。
    """
    if job_id and job_id in jobs:
        p = jobs[job_id].get("video_path")
        if p and os.path.exists(p):
            return p, None
        return None, "任务对应的视频文件不存在（可能已被清理）"
    if video_path and os.path.exists(video_path):
        return video_path, None
    return None, "缺少有效的 video_path 或 job_id"


@app.route("/api/hook-analysis", methods=["POST"])
def api_hook_analysis():
    """P0-1 前3秒黄金钩子专项分析"""
    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}
    job_id = (body.get("job_id") or "").strip()
    video_path = (body.get("video_path") or "").strip()

    vpath, err = _resolve_video(job_id, video_path)
    if err:
        return jsonify({"error": err}), 404

    # 取 ASR 分段/全文（若有）
    asr_segments = None
    asr_text = ""
    if job_id in jobs and jobs[job_id].get("result"):
        res = jobs[job_id]["result"]
        asr_segments = res.get("segments")
        asr_text = res.get("text", "")

    try:
        from media_analysis import analyze_hook
        result = analyze_hook(vpath, asr_segments=asr_segments, asr_text=asr_text)
        if result and result.get("available", True) and "error" not in result:
            try:
                db.save_analysis_result(job_id or "unknown", "hook", result)
            except Exception as _e:
                print(f"[DB] 钩子分析结果持久化失败: {_e}")
        return jsonify(result)
    except ImportError as ie:
        return jsonify({"available": False, "error": f"依赖缺失: {ie}"}), 200
    except Exception as e:
        return jsonify({"available": False, "error": f"钩子分析失败: {e}"}), 500







# ── P1 升级功能：OCR / 信息密度 / 视觉锚点 ──
# 由 p1_analysis 模块提供实现（延迟 import，缺依赖时返回错误而非崩溃）


@app.route("/api/ocr-analysis", methods=["POST"])
def api_ocr_analysis():
    """P1-1 字幕/花字 OCR"""
    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}
    job_id = (body.get("job_id") or "").strip()
    video_path = (body.get("video_path") or "").strip()
    sample_fps = int(body.get("sample_fps", 2) or 2)

    vpath, err = _resolve_video(job_id, video_path)
    if err:
        return jsonify({"error": err}), 404

    try:
        from p1_analysis import analyze_ocr
        result = analyze_ocr(vpath, sample_fps=sample_fps)
        if result and result.get("available", True) and "error" not in result:
            try:
                db.save_analysis_result(job_id or "unknown", "ocr", result)
            except Exception as _e:
                print(f"[DB] OCR 结果持久化失败: {_e}")
        return jsonify(result)
    except ImportError as ie:
        return jsonify({"available": False, "error": f"依赖缺失: {ie}"}), 200
    except Exception as e:
        return jsonify({"available": False, "error": f"OCR 分析失败: {e}"}), 500


@app.route("/api/info-density", methods=["POST"])
def api_info_density():
    """P1-2 画面信息密度"""
    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}
    job_id = (body.get("job_id") or "").strip()
    video_path = (body.get("video_path") or "").strip()

    vpath, err = _resolve_video(job_id, video_path)
    if err:
        return jsonify({"error": err}), 404

    # 取 job 上下文（转写/OCR 结果，若有）
    duration = body.get("duration")
    if duration is None and job_id in jobs:
        duration = jobs[job_id].get("duration")

    asr_text = ""
    asr_segments = None
    if job_id in jobs and jobs[job_id].get("result"):
        res = jobs[job_id]["result"]
        asr_text = res.get("text", "") or ""
        asr_segments = res.get("segments")

    ocr_results = body.get("ocr_results")

    try:
        from p1_analysis import analyze_info_density
        result = analyze_info_density(
            duration=duration,
            ocr_results=ocr_results,
            asr_text=asr_text,
            asr_segments=asr_segments,
        )
        if result and result.get("available", True) and "error" not in result:
            try:
                db.save_analysis_result(job_id or "unknown", "info_density", result)
            except Exception as _e:
                print(f"[DB] 信息密度结果持久化失败: {_e}")
        return jsonify(result)
    except ImportError as ie:
        return jsonify({"available": False, "error": f"依赖缺失: {ie}"}), 200
    except Exception as e:
        return jsonify({"available": False, "error": f"信息密度分析失败: {e}"}), 500


@app.route("/api/visual-anchor", methods=["POST"])
def api_visual_anchor():
    """P1-3 视觉锚点"""
    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}
    job_id = (body.get("job_id") or "").strip()
    video_path = (body.get("video_path") or "").strip()

    vpath, err = _resolve_video(job_id, video_path)
    if err:
        return jsonify({"error": err}), 404

    try:
        from p1_analysis import analyze_visual_anchor
        result = analyze_visual_anchor(vpath)
        if result and result.get("available", True) and "error" not in result:
            try:
                db.save_analysis_result(job_id or "unknown", "visual_anchor", result)
            except Exception as _e:
                print(f"[DB] 视觉锚点结果持久化失败: {_e}")
        return jsonify(result)
    except ImportError as ie:
        return jsonify({"available": False, "error": f"依赖缺失: {ie}"}), 200
    except Exception as e:
        return jsonify({"available": False, "error": f"视觉锚点分析失败: {e}"}), 500


# ── 启动 ──

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Video Content Analyzer Backend")

    parser.add_argument("--host", default="0.0.0.0", help="监听地址")

    parser.add_argument("--port", type=int, default=8766, help="监听端口")
    args = parser.parse_args()

    # 启动时清理 24 小时前的临时视频/WAV（防止磁盘膨胀，保留最近分析所需文件）
    try:
        import time as _t
        _cutoff = _t.time() - 24 * 3600
        for _f in TEMP_DIR.glob("*"):
            try:
                if _f.stat().st_mtime < _cutoff:
                    _f.unlink(missing_ok=True)
            except Exception:
                pass
        print("[Cleanup] 已清理 24 小时前的临时文件")
    except Exception:
        pass


    print(f"""

╔══════════════════════════════════════════════════════════════╗

║   Video Content Analyzer Backend                              ║

║   转写服务  http://{args.host}:{args.port}                        ║

║   识别引擎  Qwen3-ASR-1.7B（本地大模型，GPU DirectML+Vulkan）     ║

╚══════════════════════════════════════════════════════════════╝

  音频格式     : WAV 16kHz 单声道（soundfile 直读，不调 ffmpeg）

  依赖         : imageio-ffmpeg（音频提取）+ onnxruntime-directml

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



