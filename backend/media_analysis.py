"""
Video Content Analyzer - P0 媒体分析模块（升级功能）

包含：
  - P0-1 前3秒黄金钩子分析（MediaPipe 人脸检测 + 运动强度 + 规则分类 + 强度评分）
  - P0-2 BGM 识别与节奏匹配（librosa 纯 DSP）
  - P0-3 剪辑卡点分析（OpenCV 帧间差异 + 切镜模式 + 卡点同步率）
  - P0-4 算法兼容性评分卡（合规词规则引擎 + LLM 综合评分）

所有 import 均为延迟加载（函数内 import），缺依赖时对应功能返回
error 而非崩溃，保证服务可降级运行。

依赖：mediapipe / librosa / soundfile / opencv-python / scenedetect(可选)
"""

import os
import re
import json
import math
import time
import threading
import numpy as np

# P0 分析并发锁：MediaPipe 初始化 / ffmpeg 子进程 / OpenCV 读取在多线程并发时
# 可能死锁（实测：并发 hook-analysis 曾导致服务进程卡死无响应）。
# 强制串行执行分析，单次耗时通常在 10s 内，串行可接受。
_analysis_lock = threading.Lock()

# ============================================================
# 工具函数
# ============================================================

def _get_ffmpeg():
    """获取 imageio-ffmpeg 自带 ffmpeg 路径"""
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_audio_segment(video_path: str, wav_path: str, start: float = 0.0,
                          end: float = None, sr: int = 22050) -> bool:
    """从视频提取指定时间段的音频为 wav（pcm_s16le）。

    供 BGM 分析 / 钩子音频通道使用。返回 True=成功。
    """
    import subprocess
    from pathlib import Path
    ffmpeg = _get_ffmpeg()
    duration_opt = ""
    if end is not None:
        duration_opt = f"-t {end - start}"
    cmd = (
        f'"{ffmpeg}" -y '
        f'-ss {start} '
        f'-i "{video_path}" '
        f'-vn -acodec pcm_s16le -ar {sr} -ac 1 '
        f'{duration_opt} '
        f'"{wav_path}"'
    )
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=max(60, int(end or 60) * 2),
                                shell=True)
        return result.returncode == 0 and Path(wav_path).exists() and Path(wav_path).stat().st_size > 100
    except Exception:
        return False


def extract_first_frames(video_path: str, seconds: float = 3.0, fps: int = 30) -> list:
    """提取视频前 N 秒的帧列表（BGR ndarray）。

    返回空列表=失败。用 OpenCV VideoCapture，采样到目标 fps。
    """
    try:
        import cv2
    except ImportError:
        return []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    max_frames = int(seconds * fps)
    sample_interval = max(1, int(round(video_fps / fps)))
    frames = []
    idx = 0
    # 安全上限：最多读 total 的 1.5 倍（防损坏视频 read() 死循环）
    read_limit = max(max_frames * 2, int(total * 1.5), max_frames)
    reads = 0
    while len(frames) < max_frames and reads < read_limit:
        ret, frame = cap.read()
        reads += 1
        if not ret:
            break
        if idx % sample_interval == 0:
            frames.append(frame)
        idx += 1
        if idx / video_fps >= seconds:
            break
    cap.release()
    return frames


def calculate_motion(frames: list) -> dict:
    """计算帧间运动强度。

    返回：{mean_diff, variance, max_diff, diffs[], timestamps[]}
    """
    try:
        import cv2
    except ImportError:
        return {"mean_diff": 0.0, "variance": 0.0, "max_diff": 0.0, "diffs": [], "timestamps": []}
    if len(frames) < 2:
        return {"mean_diff": 0.0, "variance": 0.0, "max_diff": 0.0, "diffs": [], "timestamps": []}
    diffs = []
    timestamps = []
    prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    for i in range(1, len(frames)):
        gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray, prev)
        diffs.append(float(diff.mean()))
        timestamps.append(i / 30.0)
        prev = gray
    arr = np.array(diffs) if diffs else np.array([0.0])
    return {
        "mean_diff": round(float(arr.mean()), 4),
        "variance": round(float(arr.var()), 6),
        "max_diff": round(float(arr.max()), 4),
        "diffs": [round(d, 3) for d in diffs],
        "timestamps": timestamps,
    }


# ============================================================
# P0-1 前3秒黄金钩子分析
# ============================================================

class HookFaceDetector:
    """前3秒人物出镜检测器（MediaPipe BlazeFace）"""

    def __init__(self):
        self._detector = None

    def _get_detector(self):
        if self._detector is None:
            import mediapipe as mp
            self.mp_face = mp.solutions.face_detection
            self._detector = self.mp_face.FaceDetection(
                model_selection=1,
                min_detection_confidence=0.5,
            )
        return self._detector

    def detect_face_timeline(self, frames: list) -> dict:
        """逐帧检测人脸，返回出镜时间线"""
        if not frames:
            return {"first_appearance": None, "appearance_rate": 0.0, "timeline": []}
        try:
            import cv2
        except ImportError:
            return {"first_appearance": None, "appearance_rate": 0.0, "timeline": []}
        try:
            detector = self._get_detector()
        except Exception:
            return {"first_appearance": None, "appearance_rate": 0.0, "timeline": []}

        timeline = []
        for idx, frame in enumerate(frames):
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = detector.process(rgb)
                has_face = results.detections is not None
                face_count = len(results.detections) if has_face else 0
                confidence = float(max([d.score[0] for d in results.detections], default=0)) if has_face else 0
            except Exception:
                has_face, face_count, confidence = False, 0, 0
            timeline.append({
                "frame": idx,
                "timestamp": round(idx / 30.0, 3),
                "has_face": has_face,
                "face_count": face_count,
                "confidence": round(confidence, 3),
            })

        face_frames = [t for t in timeline if t["has_face"]]
        return {
            "first_appearance": round(face_frames[0]["timestamp"], 3) if face_frames else None,
            "appearance_rate": round(len(face_frames) / len(timeline), 3) if timeline else 0.0,
            "timeline": timeline,
        }


class HookClassifier:
    """前3秒钩子类型分类器（规则引擎）"""

    HOOK_PATTERNS = {
        "conflict": [
            r"千万别|不要|别再|停止|警告|千万别买|坑|骗局|智商税",
            r"以前我.*现在|曾经.*直到|后悔|教训",
        ],
        "value": [
            r"花了?\d+|[一二两三四五六七八九十百千]+\d*[元块]|只要\d+|\d+元|\d+块|成本|便宜|省钱",
            r"解决了?|搞定了?|三分钟|一分钟|快速",
            r"免费|白嫖|零成本",
        ],
        "suspense": [
            r"秘密|真相|发现了?|你不知道|没人告诉|幕后|内部",
            r"为什么|凭什么|怎么回事",
            r"第[一二三]个|最后一个",
        ],
        "resonance": [
            r"有没有人|是不是|大家都|每次|总是|又.*了",
            r"谁懂|懂的都懂|太真实了|破防了",
            r"当代年轻人|打工人的",
        ],
        "question": [
            r"你知道吗|你知道.*吗|猜猜|你猜",
            r"什么是|怎么.*呢|为什么.*呢",
            r"你有没有想过",
        ],
    }

    TYPE_NAMES = {
        "conflict": "冲突型（制造对立/痛点）",
        "value": "价值型（利益/成本）",
        "suspense": "悬念型（好奇驱动）",
        "resonance": "共鸣型（情绪认同）",
        "question": "提问型（互动引导）",
        "unknown": "未识别",
    }

    def classify(self, first_sentence: str) -> dict:
        if not first_sentence:
            return {"hook_type": "unknown", "confidence": 0.0, "matched_rules": {},
                    "fallback": "无首句文本，需 LLM 辅助判定"}
        scores = {}
        matched_rules = {}
        for hook_type, patterns in self.HOOK_PATTERNS.items():
            matches = [p for p in patterns if re.search(p, first_sentence)]
            if matches:
                scores[hook_type] = len(matches)
                matched_rules[hook_type] = matches
        if not scores:
            return {"hook_type": "unknown", "confidence": 0.0, "matched_rules": {},
                    "fallback": "需 LLM 辅助判定"}
        best_type = max(scores, key=scores.get)
        total = sum(scores.values())
        return {
            "hook_type": best_type,
            "hook_type_name": self.TYPE_NAMES.get(best_type, best_type),
            "confidence": round(scores[best_type] / total, 2),
            "matched_rules": matched_rules,
            "all_scores": scores,
        }


class HookStrengthScorer:
    """前3秒钩子强度评分（0-100）"""

    def score(self, hook_data: dict) -> dict:
        scores = {}

        hook_type = hook_data.get("hook_type", "unknown")
        if hook_type != "unknown":
            scores["hook_type"] = round(20 * hook_data.get("confidence", 0))
        else:
            scores["hook_type"] = 0

        first_sentence = hook_data.get("first_sentence", "")
        info_density = min(len(first_sentence) / 30, 1.0)
        has_keyword = any(kw in first_sentence for kw in ["你", "我", "这", "那", "什么", "怎么", "为什么"])
        scores["info_density"] = round(20 * (info_density * 0.6 + (0.4 if has_keyword else 0)))

        motion_variance = hook_data.get("motion_variance", 0)
        scores["visual_motion"] = round(20 * min(motion_variance / 0.1, 1.0))

        first_appearance = hook_data.get("first_face_appearance")
        if first_appearance is not None:
            scores["person_timing"] = round(20 * max(0, 1 - first_appearance / 3.0))
        else:
            scores["person_timing"] = 0

        audio_peak_time = hook_data.get("audio_peak_time", 999)
        if audio_peak_time <= 1.0:
            scores["audio_peak"] = 20
        elif audio_peak_time <= 2.0:
            scores["audio_peak"] = 15
        elif audio_peak_time <= 3.0:
            scores["audio_peak"] = 10
        else:
            scores["audio_peak"] = 0

        total = sum(scores.values())
        return {
            "total_score": total,
            "dimensions": scores,
            "grade": self._grade(total),
            "suggestion": self._suggest(scores),
        }

    def _grade(self, total):
        if total >= 80: return "S（强力钩子）"
        if total >= 60: return "A（有效钩子）"
        if total >= 40: return "B（弱钩子，建议优化）"
        return "C（无效钩子，必须重做前3秒）"

    def _suggest(self, scores):
        suggestions = []
        if scores.get("hook_type", 0) < 10:
            suggestions.append("首句缺少明确的钩子类型，建议加入冲突/价值/悬念关键词")
        if scores.get("person_timing", 0) < 10:
            suggestions.append("人物出镜过晚，建议在前0.5秒内出镜")
        if scores.get("visual_motion", 0) < 10:
            suggestions.append("前3秒画面变化不足，建议增加画面切换或运镜")
        if scores.get("audio_peak", 0) < 10:
            suggestions.append("音频能量峰值靠后，建议将高潮前置或增加BGM入口速度")
        return suggestions


def extract_first_sentence(segments: list, max_duration: float = 3.0) -> str:
    """从 ASR 分段中提取前3秒的首句文本。

    前3秒内无口播时，回退取最早口播句（保证钩子分析有内容可判）。
    """
    if not segments:
        return ""
    parts = []
    for seg in segments:
        start = seg.get("start", 0)
        if start > max_duration:
            break
        parts.append(seg.get("text", ""))
        if start + (seg.get("end", start) - start) >= max_duration:
            break
    text = "".join(parts).strip()
    # 前3秒无口播 → 回退最早口播句
    if not text:
        text = segments[0].get("text", "") or ""
        for seg in segments[1:]:
            if seg.get("text", "").strip():
                text = seg.get("text", "")
                break
    # 取第一句（按句号/问号/叹号切分）
    m = re.split(r"[。？！!?]", text)
    return (m[0].strip() or text[:60]) if m else text[:60]


def analyze_hook(video_path: str, asr_segments: list = None,
                 asr_text: str = "") -> dict:
    """P0-1 前3秒黄金钩子综合分析（主入口）"""
    result = {"available": True}
    start_t = time.time()
    with _analysis_lock:
        return _analyze_hook_locked(video_path, asr_segments, asr_text, start_t)


def _analyze_hook_locked(video_path: str, asr_segments, asr_text, start_t) -> dict:
    result = {"available": True}

    # 1. 画面通道：抽前3秒帧
    frames = extract_first_frames(video_path, seconds=3.0, fps=30)
    if frames:
        motion = calculate_motion(frames)
        face = HookFaceDetector().detect_face_timeline(frames)
    else:
        motion = {"variance": 0.0, "mean_diff": 0.0, "max_diff": 0.0}
        face = {"first_appearance": None, "appearance_rate": 0.0}

    # 2. 音频通道：前3秒 RMS 峰值
    audio_peak_time = None
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav3 = tf.name
        if extract_audio_segment(video_path, wav3, 0.0, 3.0, sr=16000):
            import librosa
            y, sr = librosa.load(wav3, sr=16000, mono=True)
            if len(y) > 0:
                rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
                if len(rms) > 0 and rms.max() > 0:
                    peak_idx = int(np.argmax(rms))
                    audio_peak_time = round(peak_idx * 512 / sr, 3)
        try:
            os.remove(wav3)
        except Exception:
            pass
    except Exception:
        pass

    # 3. 口播首句
    first_sentence = extract_first_sentence(asr_segments) if asr_segments else (asr_text or "")[:60]

    # 4. 钩子分类
    classifier = HookClassifier()
    hook_result = classifier.classify(first_sentence)

    # 5. 强度评分
    hook_data = {
        "hook_type": hook_result["hook_type"],
        "confidence": hook_result.get("confidence", 0),
        "first_sentence": first_sentence,
        "motion_variance": motion.get("variance", 0),
        "first_face_appearance": face.get("first_appearance"),
        "audio_peak_time": audio_peak_time if audio_peak_time is not None else 999,
    }
    score = HookStrengthScorer().score(hook_data)

    # 6. 节奏曲线（前3秒逐帧运动强度 + 音频 RMS）
    rhythm_curve = []
    for i, d in enumerate(motion.get("diffs", [])):
        rhythm_curve.append({
            "t": round(i / 30.0, 2),
            "motion": d,
            "has_face": face.get("timeline", [{}])[i + 1].get("has_face", False) if i + 1 < len(face.get("timeline", [])) else False,
        })

    result.update({
        "hook_type": hook_result["hook_type"],
        "hook_type_name": hook_result.get("hook_type_name", hook_result["hook_type"]),
        "hook_confidence": hook_result.get("confidence", 0),
        "strength_score": score["total_score"],
        "strength_grade": score["grade"],
        "first_sentence": first_sentence,
        "first_face_appearance": face.get("first_appearance"),
        "face_appearance_rate": face.get("appearance_rate", 0),
        "motion_variance": motion.get("variance", 0),
        "motion_mean": motion.get("mean_diff", 0),
        "audio_peak_time": audio_peak_time,
        "rhythm_curve": rhythm_curve,
        "suggestions": score["suggestion"],
        "dimensions": score["dimensions"],
        "matched_rules": hook_result.get("matched_rules", {}),
        "timeline": face.get("timeline", []),
        "elapsed_ms": round((time.time() - start_t) * 1000),
    })
    return result


# ============================================================
# P0-2 BGM 识别与节奏匹配（librosa 纯 DSP）
# ============================================================

class BGMAnalyzer:
    """BGM 识别与节奏匹配分析器"""

    DOUYIN_BPM_RANGE = (80, 140)

    def __init__(self, sr: int = 22050):
        self.sr = sr

    def analyze(self, audio_path: str, cut_points: list = None) -> dict:
        with _analysis_lock:
            return self._analyze_locked(audio_path, cut_points)

    def _analyze_locked(self, audio_path: str, cut_points: list = None) -> dict:
        import librosa
        y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
        duration = len(y) / sr

        # 1. 存在性检测
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        rms_mean = float(rms.mean())
        has_bgm = rms_mean > 0.01
        bgm_confidence = min(rms_mean / 0.05, 1.0)

        # 2. 节拍分析
        try:
            onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
            tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=512)
            bpm = int(round(float(tempo)))
            beat_times = [round(float(t), 3) for t in librosa.frames_to_time(beats, sr=sr, hop_length=512)]
        except Exception:
            bpm, beats, beat_times = 0, [], []

        # 3. 频谱特征
        try:
            sc = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)[0]
            sr_f = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=512)[0]
            zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=512)[0]
            sc_mean, sr_mean, zcr_mean = float(sc.mean()), float(sr_f.mean()), float(zcr.mean())
        except Exception:
            sc_mean, sr_mean, zcr_mean = 0.0, 0.0, 0.0

        # 4. 能量分析
        rms_list = [round(float(r), 6) for r in rms]
        peak_idx = int(np.argmax(rms)) if len(rms) else 0
        energy_peak_time = round(peak_idx * 512 / sr, 3)
        energy_rise_time = self._calculate_rise_time(rms, sr)

        # 5. 节奏匹配
        sync_rate = None
        if cut_points:
            sync_rate = self._calculate_sync_rate(cut_points, beat_times, tolerance=0.2)

        # 6. 风格分类
        bgm_style = self._classify_style(sc_mean, sr_mean, zcr_mean, bpm)

        # 7. 节奏评分
        rhythm_score = self._calculate_rhythm_score(
            bpm=bpm, sync_rate=sync_rate, rms_mean=rms_mean,
            rms_std=float(rms.std()), beat_regularity=self._beat_regularity(beat_times),
        )

        return {
            "has_bgm": has_bgm,
            "bgm_confidence": round(bgm_confidence, 2),
            "bpm": bpm,
            "beat_count": len(beats),
            "beat_times": beat_times,
            "energy_curve": rms_list,
            "energy_peak_time": energy_peak_time,
            "energy_rise_time": energy_rise_time,
            "spectral_centroid_mean": round(sc_mean, 2),
            "spectral_rolloff_mean": round(sr_mean, 2),
            "zero_crossing_rate_mean": round(zcr_mean, 4),
            "sync_rate": round(sync_rate, 3) if sync_rate is not None else None,
            "rhythm_score": rhythm_score,
            "bgm_style": bgm_style,
            "duration": round(duration, 2),
        }

    def _calculate_rise_time(self, rms: np.ndarray, sr: int) -> float:
        max_val = rms.max()
        if max_val == 0:
            return 0.0
        normalized = rms / max_val
        try:
            start_idx = int(np.argmax(normalized > 0.1))
            end_idx = int(np.argmax(normalized > 0.9))
            if end_idx <= start_idx:
                return 0.0
            return round((end_idx - start_idx) * 512 / sr, 3)
        except Exception:
            return 0.0

    def _calculate_sync_rate(self, cut_points: list, beat_times: list, tolerance: float = 0.2) -> float:
        if not cut_points or not beat_times:
            return 0.0
        beat_array = np.array(beat_times)
        matched = 0
        for cut_time in cut_points:
            distances = np.abs(beat_array - float(cut_time))
            if float(distances.min()) <= tolerance:
                matched += 1
        return matched / len(cut_points)

    def _beat_regularity(self, beat_times: list) -> float:
        if len(beat_times) < 3:
            return 0.5
        intervals = np.diff(beat_times)
        mean_i = np.mean(intervals)
        if mean_i == 0:
            return 0.5
        cv = float(np.std(intervals) / mean_i)
        return float(max(0, min(1 - cv, 1.0)))

    def _classify_style(self, sc_mean: float, sr_mean: float, zcr_mean: float, bpm: int) -> str:
        if zcr_mean > 0.1 and sc_mean > 3000:
            return "电子/舞曲"
        elif sc_mean > 2000 and bpm > 100:
            return "流行/节奏"
        elif sc_mean < 1500 and zcr_mean < 0.05:
            return "纯音乐/氛围"
        elif zcr_mean > 0.08:
            return "人声为主"
        else:
            return "其他"

    def _calculate_rhythm_score(self, bpm: int, sync_rate, rms_mean: float,
                                rms_std: float, beat_regularity: float) -> int:
        score = 0
        low, high = self.DOUYIN_BPM_RANGE
        if low <= bpm <= high:
            score += 30
        elif low - 10 <= bpm <= high + 10:
            score += 20
        else:
            score += 10
        if sync_rate is not None:
            score += round(30 * sync_rate)
        else:
            score += 15
        if rms_mean > 0.02 and rms_std > 0.005:
            score += 20
        elif rms_mean > 0.01:
            score += 12
        else:
            score += 5
        score += round(20 * beat_regularity)
        return min(score, 100)


# ============================================================
# P0-3 剪辑卡点分析（OpenCV 帧间差异）
# ============================================================

class RhythmAnalyzer:
    """剪辑卡点分析器"""

    CUT_DIFF_THRESHOLD = 30.0
    MIN_CUT_INTERVAL = 0.3
    SYNC_TOLERANCE = 0.2
    SYNC_THRESHOLD = 0.6

    def analyze(self, video_path: str, beat_times: list = None, sample_fps: int = 10) -> dict:
        with _analysis_lock:
            return self._analyze_locked(video_path, beat_times, sample_fps)

    def _analyze_locked(self, video_path: str, beat_times: list = None, sample_fps: int = 10) -> dict:
        frames_data = self._compute_frame_diffs(video_path, sample_fps)
        if not frames_data or not frames_data.get("diffs"):
            return {"available": False, "error": "无法读取视频帧"}

        raw_cuts = self._detect_cuts(frames_data)
        duration = frames_data["duration"]
        cut_frequency = self._calculate_frequency(raw_cuts, duration)
        avg_interval = self._calculate_avg_interval(raw_cuts)
        cut_pattern = self._classify_pattern(avg_interval)

        sync_rate = 0.0
        cut_points_with_beats = []
        if beat_times:
            cut_points_with_beats = self._match_beats(raw_cuts, beat_times)
            sync_rate = sum(1 for cp in cut_points_with_beats if cp["on_beat"]) / max(len(cut_points_with_beats), 1)
        else:
            cut_points_with_beats = raw_cuts

        rhythm_curve = self._build_rhythm_curve(frames_data, beat_times)
        rhythm_score = self._score(cut_frequency, sync_rate, avg_interval, duration)
        suggestions = self._suggest(cut_pattern, sync_rate, cut_frequency, rhythm_curve)

        return {
            "available": True,
            "cut_points": cut_points_with_beats,
            "cut_count": len(raw_cuts),
            "cut_frequency": round(cut_frequency, 2),
            "avg_cut_interval": round(avg_interval, 2),
            "cut_pattern": cut_pattern,
            "sync_rate": round(sync_rate, 3),
            "rhythm_score": rhythm_score,
            "rhythm_curve": rhythm_curve,
            "is_beat_synced": sync_rate >= self.SYNC_THRESHOLD,
            "suggestions": suggestions,
            "duration": round(duration, 2),
        }

    def _compute_frame_diffs(self, video_path: str, sample_fps: int) -> dict:
        try:
            import cv2
        except ImportError:
            return None
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / video_fps if video_fps else 0

        sample_interval = max(1, int(round(video_fps / sample_fps)))
        prev_frame = None
        diffs, timestamps = [], []
        idx = 0
        # 安全上限：防损坏视频 read() 死循环
        read_limit = max(frame_count * 1.5, 3000)
        reads = 0
        while reads < read_limit:
            ret, frame = cap.read()
            reads += 1
            if not ret:
                break
            if idx % sample_interval == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                timestamp = idx / video_fps
                if prev_frame is not None:
                    diff = cv2.absdiff(gray, prev_frame)
                    diffs.append(float(diff.mean()))
                    timestamps.append(timestamp)
                prev_frame = gray
            idx += 1
        cap.release()
        return {"diffs": diffs, "timestamps": timestamps, "duration": duration,
                "sample_fps": sample_fps}

    def _detect_cuts(self, frames_data: dict) -> list:
        diffs, timestamps = frames_data["diffs"], frames_data["timestamps"]
        if not diffs:
            return []
        mean_diff = float(np.mean(diffs))
        std_diff = float(np.std(diffs))
        threshold = max(self.CUT_DIFF_THRESHOLD, mean_diff + 2 * std_diff)
        cuts = []
        last_cut_time = -1
        for i, diff in enumerate(diffs):
            if diff > threshold:
                ts = timestamps[i]
                if ts - last_cut_time >= self.MIN_CUT_INTERVAL:
                    cuts.append({"timestamp": round(ts, 3), "frame_idx": i,
                                 "diff_score": round(diff, 2)})
                    last_cut_time = ts
        return cuts

    def _calculate_frequency(self, cuts: list, duration: float) -> float:
        if duration == 0:
            return 0
        return len(cuts) / duration * 60

    def _calculate_avg_interval(self, cuts: list) -> float:
        if len(cuts) < 2:
            return 0
        intervals = [cuts[i + 1]["timestamp"] - cuts[i]["timestamp"] for i in range(len(cuts) - 1)]
        return float(np.mean(intervals))

    def _classify_pattern(self, avg_interval: float) -> str:
        if avg_interval == 0:
            return "unknown"
        if avg_interval < 1.0:
            return "快切（卡点视频风格）"
        elif avg_interval <= 3.0:
            return "中切（口播视频风格）"
        else:
            return "慢切（叙事视频风格）"

    def _match_beats(self, cuts: list, beat_times: list) -> list:
        beat_array = np.array(beat_times)
        result = []
        for cut in cuts:
            ct = cut["timestamp"]
            distances = np.abs(beat_array - ct)
            min_dist = float(distances.min()) if len(distances) > 0 else 999
            nearest_beat = float(beat_array[np.argmin(distances)]) if len(distances) > 0 else None
            cut_copy = cut.copy()
            cut_copy["matched_beat"] = round(nearest_beat, 3) if nearest_beat is not None else None
            cut_copy["beat_distance"] = round(min_dist, 3)
            cut_copy["on_beat"] = min_dist <= self.SYNC_TOLERANCE
            result.append(cut_copy)
        return result

    def _build_rhythm_curve(self, frames_data: dict, beat_times: list) -> list:
        diffs, timestamps = frames_data["diffs"], frames_data["timestamps"]
        duration = frames_data["duration"]
        seconds = int(math.ceil(duration))
        curve = []
        for sec in range(max(seconds, 1)):
            mask = [(t >= sec and t < sec + 1) for t in timestamps]
            sec_diffs = [d for d, m in zip(diffs, mask) if m]
            avg_diff = float(np.mean(sec_diffs)) if sec_diffs else 0
            beat_count = sum(1 for bt in (beat_times or []) if sec <= bt < sec + 1)
            curve.append({"second": sec, "motion_intensity": round(avg_diff, 2), "beat_count": beat_count})
        return curve

    def _score(self, frequency: float, sync_rate: float, avg_interval: float, duration: float) -> int:
        score = 0
        if 10 <= frequency <= 30:
            score += 30
        elif 5 <= frequency <= 40:
            score += 20
        else:
            score += 10
        score += round(40 * sync_rate)
        if 0.5 <= avg_interval <= 3.0:
            score += 30
        elif 0.3 <= avg_interval <= 5.0:
            score += 20
        else:
            score += 10
        return min(score, 100)

    def _suggest(self, pattern: str, sync_rate: float, frequency: float, curve: list) -> list:
        suggestions = []
        if sync_rate < 0.3 and pattern == "快切（卡点视频风格）":
            suggestions.append("切镜与BGM节拍同步率低，建议重新对齐切镜点到节拍")
        if frequency < 5:
            suggestions.append("切镜频率过低，观众容易流失，建议增加画面变化")
        low_motion_streak = 0
        for point in curve:
            if point["motion_intensity"] < 5 and point["beat_count"] == 0:
                low_motion_streak += 1
                if low_motion_streak >= 3:
                    suggestions.append(f'第{point["second"]-2}-{point["second"]}秒节奏断档，建议增加画面切换或BGM高潮')
                    break
            else:
                low_motion_streak = 0
        if not suggestions:
            suggestions.append("剪辑节奏良好，无明显优化点")
        return suggestions


# ============================================================
# P0-4 算法兼容性评分卡
# ============================================================

class ComplianceChecker:
    """抖音广告法合规检测器"""

    ABSOLUTE_WORDS = [
        "最", "第一", "顶级", "极致", "完美", "绝对", "100%",
        "首个", "独家", "唯一", "万能", "永久", "永不",
        "国家级", "世界级", "全网", "全国",
    ]
    MEDICAL_WORDS = [
        "治疗", "治愈", "疗效", "药到病除", "根治",
        "减肥", "瘦身", "丰胸", "壮阳", "抗癌",
        "降血压", "降血糖", "降血脂",
    ]
    EXTERNAL_LINK_WORDS = [
        "加微信", "加V", "微信号", "扫码加",
        "点击链接", "访问网址", "淘宝搜索",
        "小红书", "快手", "B站", "公众号",
    ]

    def check(self, transcription: str) -> dict:
        risks = {"absolute_words": [], "medical_words": [], "external_link_words": [],
                 "risk_level": "low"}
        if not transcription:
            return risks
        for word in self.ABSOLUTE_WORDS:
            if word in transcription:
                risks["absolute_words"].append(word)
        for word in self.MEDICAL_WORDS:
            if word in transcription:
                risks["medical_words"].append(word)
        for word in self.EXTERNAL_LINK_WORDS:
            if word in transcription:
                risks["external_link_words"].append(word)
        total_risks = sum(len(v) for v in risks.values() if isinstance(v, list))
        if total_risks >= 5 or len(risks["medical_words"]) >= 2:
            risks["risk_level"] = "high"
        elif total_risks >= 2:
            risks["risk_level"] = "medium"
        return risks


ALGORITHM_SCORE_PROMPT = """你是一位抖音算法分析专家。请基于以下视频分析数据，输出算法兼容性评分。

## 输入数据
- 视频时长：{duration}秒
- 钩子分析：类型={hook_type}，强度评分={hook_score}/100
- BGM分析：BPM={bpm}，节奏评分={bgm_rhythm}/100
- 卡点分析：同步率={sync_rate}，切镜频率={cut_frequency}次/分钟
- 口播转写：{transcription_excerpt}
- 合规检测结果：{compliance_result}

## 评分维度（满分100）
1. 钩子强度（25分）：基于钩子类型、强度评分、首句内容
2. 完播率预估（25分）：基于时长合理性、信息密度、剪辑节奏
3. 互动潜力（20分）：基于争议点、共鸣点、行动召唤
4. 转化潜力（15分）：基于卖点清晰度、信任背书、紧迫感
5. 算法友好度（15分）：基于合规性、画面风险、审核风险

## 输出格式（只输出JSON，不要其他内容）
```json
{{
  "total_score": 78,
  "dimensions": {{
    "hook_strength": {{"score": 22, "max": 25, "comment": "..."}},
    "completion_rate": {{"score": 18, "max": 25, "comment": "..."}},
    "interaction_potential": {{"score": 15, "max": 20, "comment": "..."}},
    "conversion_potential": {{"score": 12, "max": 15, "comment": "..."}},
    "algorithm_friendliness": {{"score": 11, "max": 15, "comment": "..."}}
  }},
  "traffic_pool_prediction": "推荐池",
  "compliance_risks": ["检测到绝对词'最'"],
  "optimization_suggestions": ["建议将卖点前置到前10秒"]
}}
```
"""


def _extract_json_from_llm(text: str) -> dict:
    """从 LLM 输出中提取 JSON"""
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```json\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def analyze_algorithm_score(duration: float, hook_analysis: dict = None,
                            bgm_analysis: dict = None, rhythm_analysis: dict = None,
                            transcription: str = "", llm_fn=None) -> dict:
    """P0-4 算法兼容性评分（规则层 + 可选 LLM 层）

    llm_fn: 可选回调，签名 llm_fn(prompt) -> str，返回 LLM 文本。
           为 None 时只做规则评分。
    """
    compliance = ComplianceChecker().check(transcription or "")

    # 规则评分（本地可算的部分）
    hook_score = (hook_analysis or {}).get("strength_score", 0)
    bgm_rhythm = (bgm_analysis or {}).get("rhythm_score", 0)
    sync_rate = (rhythm_analysis or {}).get("sync_rate", 0)
    cut_frequency = (rhythm_analysis or {}).get("cut_frequency", 0)
    hook_type = (hook_analysis or {}).get("hook_type", "unknown")
    bpm = (bgm_analysis or {}).get("bpm", 0)

    # 合规扣分：每个风险词 -3，最高扣 15
    risk_count = (len(compliance["absolute_words"]) + len(compliance["medical_words"])
                  + len(compliance["external_link_words"]))
    compliance_base = max(0, 15 - risk_count * 3)

    rule_total = min(100, round(
        hook_score * 0.25
        + bgm_rhythm * 0.15
        + (sync_rate * 100) * 0.10
        + compliance_base
    ))

    result = {
        "available": True,
        "rule_score": rule_total,
        "compliance": compliance,
        "hook_score": hook_score,
        "bgm_rhythm_score": bgm_rhythm,
        "sync_rate": sync_rate,
        "cut_frequency": cut_frequency,
    }

    # LLM 层（可选）
    if llm_fn:
        try:
            prompt = ALGORITHM_SCORE_PROMPT.format(
                duration=duration or 0,
                hook_type=hook_type,
                hook_score=hook_score,
                bpm=bpm,
                bgm_rhythm=bgm_rhythm,
                sync_rate=sync_rate,
                cut_frequency=cut_frequency,
                transcription_excerpt=(transcription or "")[:800],
                compliance_result=json.dumps(compliance, ensure_ascii=False),
            )
            llm_text = llm_fn(prompt)
            llm_data = _extract_json_from_llm(llm_text)
            if llm_data:
                result["llm_score"] = llm_data
                result["total_score"] = llm_data.get("total_score", rule_total)
                result["dimensions"] = llm_data.get("dimensions", {})
                result["traffic_pool_prediction"] = llm_data.get("traffic_pool_prediction", "")
                result["optimization_suggestions"] = llm_data.get("optimization_suggestions", [])
            else:
                result["total_score"] = rule_total
        except Exception as e:
            result["total_score"] = rule_total
            result["llm_error"] = str(e)
    else:
        result["total_score"] = rule_total

    # 等级
    total = result.get("total_score", rule_total)
    if total >= 80:
        result["grade"] = "S（优质，推荐投流）"
    elif total >= 65:
        result["grade"] = "A（良好，可投流）"
    elif total >= 50:
        result["grade"] = "B（一般，优化后投流）"
    else:
        result["grade"] = "C（较差，不建议投流）"
    return result
