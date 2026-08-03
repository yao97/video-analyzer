"""
Video Content Analyzer - 媒体分析模块（升级功能精简版）

包含：
  - 前3秒黄金钩子分析（MediaPipe 人脸检测 + 运动强度 + 三分类规则 + 强度评分 + 能量曲线）
  - ComplianceChecker 合规词规则引擎（保留供 P1 使用）

已按产品决策裁剪：
  - BGM 独立接口 → 砍，仅保留全片能量曲线并入钩子分析输出
  - 剪辑卡点分析 → 全砍（景区视频不需要）
  - 算法 LLM 综合评分 → 砍，合规词规则引擎保留

所有 import 均为延迟加载（函数内 import），缺依赖时对应功能返回
error 而非崩溃，保证服务可降级运行。

依赖：mediapipe / librosa / soundfile / opencv-python
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
    """前3秒钩子类型分类器（规则引擎，三分类）

    三类：
      - visual_impact  视觉冲击（画面/运动/出镜驱动）
      - benefit        利益（价格/效果/效率驱动）
      - counter_intu  反认知（冲突/悬念/颠覆常识驱动）
    """

    HOOK_PATTERNS = {
        "benefit": [
            r"花了?\d+|[一二两三四五六七八九十百千]+\d*[元块]|只要\d+|\d+元|\d+块|成本|便宜|省钱",
            r"解决了?|搞定了?|三分钟|一分钟|快速|免费|白嫖|零成本",
            r"省|赚|送|优惠|折扣|划算",
        ],
        "counter_intu": [
            r"千万别|不要|别再|停止|警告|千万别买|坑|骗局|智商税|后悔|教训",
            r"秘密|真相|发现了?|你不知道|没人告诉|幕后|内部|竟然|居然",
            r"为什么|凭什么|怎么回事|打破|颠覆|反常识",
            r"以前我.*现在|曾经.*直到",
        ],
    }

    TYPE_NAMES = {
        "visual_impact": "视觉冲击（画面/运动/出镜）",
        "benefit": "利益（价格/效果/效率）",
        "counter_intu": "反认知（冲突/悬念/颠覆）",
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
        # 并列时优先反认知（强否定/悬念词信号更强，如"千万别/坑/骗局"）
        best_type = max(scores, key=lambda k: (scores[k], 1 if k == "counter_intu" else 0))
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
            suggestions.append("首句缺少明确的钩子类型，建议加入利益/反认知关键词")
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

    # 2. 音频通道：前3秒 RMS 峰值 + 全片逐秒能量曲线
    audio_peak_time = None
    energy_curve = []
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav_path = tf.name
        if extract_audio_segment(video_path, wav_path, 0.0, None, sr=16000):
            import librosa
            y, sr = librosa.load(wav_path, sr=16000, mono=True)
            if len(y) > 0:
                rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
                if len(rms) > 0:
                    # 前3秒峰值（用于钩子评分）
                    if rms.max() > 0:
                        peak_idx = int(np.argmax(rms))
                        audio_peak_time = round(peak_idx * 512 / sr, 3)
                    # 全片逐秒能量曲线（原 BGM 接口保留的价值数据）
                    hop_sec = 512 / sr
                    rms_len = len(rms)
                    n_sec = max(1, int(rms_len * hop_sec))
                    for s in range(n_sec):
                        lo = int(s / hop_sec)
                        hi = int((s + 1) / hop_sec)
                        seg = rms[lo:min(hi, rms_len)]
                        energy_curve.append({
                            "t": s,
                            "energy": round(float(seg.mean()), 5) if len(seg) else 0,
                        })
        try:
            os.remove(wav_path)
        except Exception:
            pass
    except Exception:
        pass

    # 3. 口播首句
    first_sentence = extract_first_sentence(asr_segments) if asr_segments else (asr_text or "")[:60]

    # 4. 钩子分类（三分类：visual_impact / benefit / counter_intu）
    classifier = HookClassifier()
    hook_result = classifier.classify(first_sentence)

    # 视觉冲击兜底：文本未命中规则，但画面变化强或有人物出镜 → 归类视觉冲击
    if hook_result["hook_type"] == "unknown":
        motion_mean = motion.get("mean_diff", 0)
        has_face_early = face.get("first_appearance") is not None and face.get("first_appearance") <= 1.5
        if motion_mean > 8 or has_face_early:
            hook_result["hook_type"] = "visual_impact"
            hook_result["hook_type_name"] = HookClassifier.TYPE_NAMES["visual_impact"]
            hook_result["confidence"] = 0.6
            hook_result["matched_rules"] = {"visual_impact": ["画面运动/人物出镜"]}

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
        "energy_curve": energy_curve,
        "rhythm_curve": rhythm_curve,
        "suggestions": score["suggestion"],
        "dimensions": score["dimensions"],
        "matched_rules": hook_result.get("matched_rules", {}),
        "timeline": face.get("timeline", []),
        "elapsed_ms": round((time.time() - start_t) * 1000),
    })
    return result


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


