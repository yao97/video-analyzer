"""
Video Content Analyzer - P1 分析模块（OCR / 信息密度 / 视觉锚点）

包含：
  - P1-1 SubtitleOCR：字幕/花字 OCR（PaddleOCR，检测+识别+方向分类）
  - P1-2 画面信息密度：有效秒数占比 + 空白段标注 + 卖点首次出现时间
  - P1-3 视觉锚点：全片视觉最炸画面定位（类型分类 + 封面建议）

所有 import 均为延迟加载（函数内 import），缺依赖时对应功能返回
error 而非崩溃，保证服务可降级运行。

依赖：paddleocr / paddlepaddle / opencv-python / numpy
"""

import os
import re
import time
import threading
import numpy as np

# 与 media_analysis 共享的全局分析锁：OCR/画面分析同样涉及 OpenCV 与
# 模型推理，多线程并发可能死锁，强制串行执行。
_analysis_lock = threading.Lock()


# ============================================================
# P1-1 字幕/花字 OCR
# ============================================================

class SubtitleOCR:
    """字幕/花字 OCR 提取器（PaddleOCR）"""

    def __init__(self, lang: str = "ch"):
        self.lang = lang
        self._ocr = None

    def _get_ocr(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                show_log=False,
                use_gpu=False,
            )
        return self._ocr

    def extract(self, video_path: str, sample_fps: int = 2) -> dict:
        """从视频提取字幕/花字。

        返回：
        {
            "results": [{timestamp, frame_idx, texts: [...]}],
            "subtitle_timeline": [{timestamp, texts: [...]}],
            "total_text_count": N,
            "subtitle_count": N,
            "decoration_count": N,
            "available": True,
        }
        """
        try:
            import cv2
        except ImportError:
            return {"available": False, "error": "缺少 opencv-python 依赖"}

        # 初始化 OCR（懒加载，首次会下载模型 ~50MB）
        try:
            ocr = self._get_ocr()
        except ImportError as ie:
            return {"available": False, "error": f"缺少 paddleocr 依赖: {ie}"}
        except Exception as e:
            return {"available": False, "error": f"OCR 初始化失败: {e}"}

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"available": False, "error": "无法读取视频"}
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / video_fps if video_fps else 0
        sample_interval = max(1, int(round(video_fps / sample_fps)))
        read_limit = max(int(frame_count * 1.5), 3000)

        results = []
        frame_idx = 0
        reads = 0
        while reads < read_limit:
            ret, frame = cap.read()
            reads += 1
            if not ret:
                break
            if frame_idx % sample_interval == 0:
                timestamp = round(frame_idx / video_fps, 3)
                ocr_data = self._ocr_frame(ocr, frame, frame_idx, timestamp)
                results.append(ocr_data)
            frame_idx += 1
        cap.release()

        # 后处理：去重 + 时间轴合并
        merged = self._post_process(results)
        timeline = self._get_subtitle_timeline(merged)

        total_count = sum(len(r["texts"]) for r in merged)
        sub_count = sum(1 for r in merged for t in r["texts"] if t["is_subtitle"])
        dec_count = total_count - sub_count

        return {
            "available": True,
            "results": merged,
            "subtitle_timeline": timeline,
            "total_text_count": total_count,
            "subtitle_count": sub_count,
            "decoration_count": dec_count,
            "duration": round(duration, 2),
            "frame_count": len(merged),
        }

    def _ocr_frame(self, ocr, frame, idx: int, timestamp: float) -> dict:
        """单帧 OCR"""
        try:
            result = ocr.ocr(frame, cls=True)
        except Exception:
            result = None

        texts = []
        if result and result[0]:
            for line in result[0]:
                try:
                    box = line[0]          # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    text = line[1][0]      # 文字内容
                    confidence = float(line[1][1])
                    is_subtitle = self._is_subtitle(box, frame.shape)
                    texts.append({
                        "text": text,
                        "confidence": round(confidence, 3),
                        "position": [[round(p[0], 1), round(p[1], 1)] for p in box],
                        "is_subtitle": is_subtitle,
                        "position_type": "subtitle" if is_subtitle else "decoration",
                    })
                except Exception:
                    continue

        return {"timestamp": timestamp, "frame_idx": idx, "texts": texts}

    @staticmethod
    def _is_subtitle(box: list, frame_shape: tuple) -> bool:
        """底部 70% 以下区域 → 字幕"""
        h, w = frame_shape[:2]
        if h == 0:
            return False
        ys = [p[1] for p in box]
        center_y = sum(ys) / len(ys)
        return center_y / h > 0.7

    def _post_process(self, results: list) -> list:
        """相邻帧去重：只保留新增文字"""
        if not results:
            return results
        merged = []
        prev_texts = set()
        for result in results:
            current_texts = set(t["text"] for t in result["texts"] if t["confidence"] > 0.6)
            new_texts = current_texts - prev_texts
            if new_texts:
                filtered = [t for t in result["texts"] if t["text"] in new_texts]
                merged.append({"timestamp": result["timestamp"],
                               "frame_idx": result["frame_idx"],
                               "texts": filtered})
            prev_texts = current_texts
        return merged

    @staticmethod
    def _get_subtitle_timeline(results: list) -> list:
        """提取纯字幕时间轴（不含花字）"""
        timeline = []
        for result in results:
            subtitles = [t for t in result["texts"] if t["is_subtitle"]]
            if subtitles:
                timeline.append({
                    "timestamp": result["timestamp"],
                    "texts": [t["text"] for t in subtitles],
                })
        return timeline


# ============================================================
# P1-2 画面信息密度
# ============================================================

# 价格/卖点关键词（识别第一条价格信息出现时间）
PRICE_PATTERNS = [
    r"\d+[\.\d]*\s*(元|块|毛|分)",
    r"只要\s*\d+",
    r"原价\s*\d+",
    r"限时.*\d+.*元",
    r"秒杀价",
    r"特价\s*\d+",
    r"[¥￥]\s*\d+",
    r"\d+\.?\d*\s*(折|折起)",
]


def analyze_info_density(duration: float, ocr_results: dict = None,
                         motion_curve: list = None, asr_text: str = "",
                         asr_segments: list = None) -> dict:
    """P1-2 画面信息密度分析。

    输入：
      duration      视频总时长（秒）
      ocr_results   OCR 分析结果（含 subtitle_timeline / results）
      motion_curve  逐秒运动强度曲线（[{"t": s, "motion": v}, ...]，可选）
      asr_text      转写全文（卖点定位用）
      asr_segments  转写分段（卖点定位用）

    输出：
      info_density   有效秒数占比 0-1
      blank_segments 空白段列表 [{start, end, reason}]
      sell_point     {first_time, text, warning} 卖点首次出现
      density_score  综合评分 0-100
    """
    result = {"available": True}

    # 1. 有效秒数判定：该秒有 OCR 文字 或 运动强度超阈值 或 有口播
    duration_sec = max(1, int(duration or 0))
    has_info = [False] * duration_sec

    # OCR 文字出现时间
    if ocr_results and ocr_results.get("results"):
        for r in ocr_results["results"]:
            if r.get("texts"):
                t = int(r.get("timestamp", 0))
                if 0 <= t < duration_sec:
                    has_info[t] = True

    # 口播出现时间
    if asr_segments:
        for seg in asr_segments:
            start = int(seg.get("start", 0))
            end = int(seg.get("end", start + 1))
            for t in range(max(0, start), min(duration_sec, end + 1)):
                has_info[t] = True

    # 运动强度超阈值
    if motion_curve:
        for point in motion_curve:
            t = int(point.get("t", 0))
            if 0 <= t < duration_sec and point.get("motion", 0) > 5:
                has_info[t] = True

    # 2. 有效秒数占比
    valid_seconds = sum(has_info)
    info_density = round(valid_seconds / duration_sec, 3) if duration_sec else 0

    # 3. 空白段标注（连续 >= 2 秒无信息）
    blank_segments = []
    start_blank = None
    for t in range(duration_sec):
        if not has_info[t]:
            if start_blank is None:
                start_blank = t
        else:
            if start_blank is not None:
                if t - start_blank >= 2:
                    blank_segments.append({
                        "start": start_blank, "end": t - 1,
                        "duration": t - start_blank,
                        "reason": "无新信息（无文字/低运动/无口播）",
                    })
                start_blank = None
    if start_blank is not None and duration_sec - start_blank >= 2:
        blank_segments.append({
            "start": start_blank, "end": duration_sec - 1,
            "duration": duration_sec - start_blank,
            "reason": "无新信息（无文字/低运动/无口播）",
        })

    # 4. 卖点首次出现时间
    sell_point = {"first_time": None, "text": "", "warning": False}
    search_text = (asr_text or "") + " " + " ".join(
        t["text"] for r in (ocr_results or {}).get("results", []) for t in r["texts"]
    )
    if search_text:
        # 先按时间定位：OCR 文字优先（有时间戳）
        first_time = None
        first_text = ""
        if ocr_results and ocr_results.get("results"):
            for r in sorted(ocr_results["results"], key=lambda x: x.get("timestamp", 0)):
                for t in r.get("texts", []):
                    if re.search("|".join(PRICE_PATTERNS), t["text"]):
                        first_time = r.get("timestamp")
                        first_text = t["text"]
                        break
                if first_time is not None:
                    break
        if first_time is None and asr_segments:
            # 从口播分段定位
            for seg in sorted(asr_segments, key=lambda x: x.get("start", 0)):
                if re.search("|".join(PRICE_PATTERNS), seg.get("text", "")):
                    first_time = seg.get("start")
                    first_text = seg.get("text", "")[:40]
                    break
        sell_point = {
            "first_time": first_time,
            "text": first_text,
            "warning": first_time is not None and first_time > 8,
        }

    # 5. 综合评分
    density_score = min(100, round(
        info_density * 70            # 有效占比 70 分
        + (30 if sell_point["first_time"] is not None and not sell_point["warning"] else
           15 if sell_point["first_time"] is not None else 0)  # 卖点前置 30 分
    ))

    result.update({
        "info_density": info_density,
        "valid_seconds": valid_seconds,
        "total_seconds": duration_sec,
        "blank_segments": blank_segments,
        "sell_point": sell_point,
        "density_score": density_score,
        "grade": "高" if density_score >= 75 else "中" if density_score >= 50 else "低",
    })
    return result


# ============================================================
# P1-3 视觉锚点
# ============================================================

class VisualAnchorDetector:
    """视觉锚点：全片视觉最炸画面定位"""

    def analyze(self, video_path: str, sample_fps: int = 10) -> dict:
        """定位全片视觉最强画面。

        判定维度：
          - 运动强度（帧间差异）
          - 亮度变化（灯光亮灯）
          - 色彩丰富度（全景展开）

        返回：
        {
            "anchor_time": 12.5,        # 最炸画面秒数
            "anchor_type": "运动拉升",   # 灯光亮灯/全景展开/运动拉升
            "anchor_score": 92,          # 0-100
            "suggestion": "...",         # 封面/前置建议
            "top_moments": [...],        # Top5 视觉时刻
            "curve": [...],              # 逐秒视觉强度曲线
        }
        """
        try:
            import cv2
        except ImportError:
            return {"available": False, "error": "缺少 opencv-python 依赖"}

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"available": False, "error": "无法读取视频"}
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / video_fps if video_fps else 0
        sample_interval = max(1, int(round(video_fps / sample_fps)))
        read_limit = max(int(frame_count * 1.5), 3000)

        prev_gray = None
        prev_brightness = 0.0
        diffs, brightnesses, timestamps = [], [], []
        idx = 0
        reads = 0
        while reads < read_limit:
            ret, frame = cap.read()
            reads += 1
            if not ret:
                break
            if idx % sample_interval == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                timestamp = idx / video_fps
                brightness = float(gray.mean())
                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    diffs.append(float(diff.mean()))
                    brightnesses.append(abs(brightness - prev_brightness))
                    timestamps.append(timestamp)
                prev_gray = gray
                prev_brightness = brightness
            idx += 1
        cap.release()

        if not diffs:
            return {"available": False, "error": "无法提取画面帧"}

        # 逐秒聚合视觉强度：运动 + 亮度突变 + 色彩（色彩用运动近似）
        seconds = max(1, int(duration))
        sec_motion = [0.0] * seconds
        sec_bright = [0.0] * seconds
        sec_count = [0] * seconds
        for i, ts in enumerate(timestamps):
            s = min(seconds - 1, int(ts))
            sec_motion[s] += diffs[i]
            sec_bright[s] += brightnesses[i]
            sec_count[s] += 1
        for s in range(seconds):
            if sec_count[s] > 0:
                sec_motion[s] /= sec_count[s]
                sec_bright[s] /= sec_count[s]

        # 视觉强度 = 运动 * 0.7 + 亮度突变 * 0.3（归一化）
        max_motion = max(sec_motion) or 1
        max_bright = max(sec_bright) or 1
        curve = []
        for s in range(seconds):
            intensity = (sec_motion[s] / max_motion) * 70 + (sec_bright[s] / max_bright) * 30
            curve.append({
                "t": s,
                "motion": round(sec_motion[s], 2),
                "brightness_change": round(sec_bright[s], 2),
                "intensity": round(intensity, 1),
            })

        # Top5 视觉时刻 + 类型判定
        sorted_idx = sorted(range(seconds), key=lambda s: curve[s]["intensity"], reverse=True)
        top5 = []
        used = set()
        for s in sorted_idx:
            if len(top5) >= 5:
                break
            if s in used:
                continue
            # 相邻 2 秒去重（同一镜头）
            if any(abs(s - u) <= 2 for u in used):
                continue
            used.add(s)
            top5.append(curve[s])

        anchor = top5[0] if top5 else curve[0]
        anchor_time = anchor["t"]
        anchor_type = self._classify_anchor(anchor)

        suggestion = ""
        if anchor_time > 3:
            suggestion = (f"全片视觉最炸画面在第 {anchor_time} 秒（{anchor_type}）。"
                          f"已超过前3秒黄金区，建议截图做封面，或把这段剪到前 3 秒。")
        else:
            suggestion = (f"视觉最强画面在前 {anchor_time} 秒内出现（{anchor_type}），"
                          f"钩子位置优秀，可直接复用做封面。")

        return {
            "available": True,
            "anchor_time": anchor_time,
            "anchor_type": anchor_type,
            "anchor_score": round(anchor["intensity"], 1),
            "suggestion": suggestion,
            "top_moments": top5,
            "curve": curve,
            "duration": round(duration, 2),
        }

    @staticmethod
    def _classify_anchor(point: dict) -> str:
        """按维度特征分类锚点类型"""
        motion = point.get("motion", 0)
        bright = point.get("brightness_change", 0)
        if bright > motion * 1.5 and bright > 5:
            return "灯光亮灯/明暗切换"
        if motion > 15:
            return "运动拉升/镜头切换"
        if motion > 8:
            return "运动推进"
        return "画面展开"


# 模块级函数入口（带锁）
def analyze_ocr(video_path: str, sample_fps: int = 2) -> dict:
    """P1-1 入口（加锁串行）"""
    with _analysis_lock:
        return SubtitleOCR().extract(video_path, sample_fps=sample_fps)


def analyze_visual_anchor(video_path: str, sample_fps: int = 10) -> dict:
    """P1-3 入口（加锁串行）"""
    with _analysis_lock:
        return VisualAnchorDetector().analyze(video_path, sample_fps=sample_fps)
