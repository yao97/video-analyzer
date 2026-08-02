"""
场景检测器
基于内容变化检测视频场景切换
"""
import cv2
import numpy as np
from typing import Optional
from loguru import logger

from ..schemas.video_analysis import SceneInfo


class SceneDetector:
    """
    视频场景检测器
    检测视频中的场景切换点
    """

    def __init__(
        self,
        threshold: float = 30.0,
        min_scene_duration: float = 1.0,
    ):
        """
        Args:
            threshold: 场景切换阈值 (越大越不敏感)
            min_scene_duration: 最小场景持续时间(秒)
        """
        self._threshold = threshold
        self._min_scene_duration = min_scene_duration
        self._prev_hist = None

    def calculate_histogram_diff(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """计算两张帧的直方图差异"""
        # 转为灰度
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # 缩小加速
        gray1 = cv2.resize(gray1, (256, 256))
        gray2 = cv2.resize(gray2, (256, 256))
        
        # 计算直方图
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        
        # 归一化
        cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
        
        # 计算相似度 (0=完全不同, 1=完全相同)
        similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        # 返回差异度
        diff = 1.0 - max(0, similarity)  # correlation 范围是 [-1, 1]
        return float(diff)

    def calculate_color_histogram(self, frame: np.ndarray) -> np.ndarray:
        """计算彩色直方图"""
        # 缩小加速
        small = cv2.resize(frame, (128, 128))
        
        # 分别计算 BGR 三通道直方图
        hist_b = cv2.calcHist([small], [0], None, [64], [0, 256])
        hist_g = cv2.calcHist([small], [1], None, [64], [0, 256])
        hist_r = cv2.calcHist([small], [2], None, [64], [0, 256])
        
        # 归一化
        cv2.normalize(hist_b, hist_b, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(hist_g, hist_g, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(hist_r, hist_r, 0, 1, cv2.NORM_MINMAX)
        
        return np.concatenate([hist_b, hist_g, hist_r])

    def detect_scenes(
        self,
        video_path: str,
        fps: float = 30.0,
    ) -> list[SceneInfo]:
        """
        检测视频中的场景
        
        Args:
            video_path: 视频路径
            fps: 视频帧率
            
        Returns:
            场景列表
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频: {video_path}")
        
        scenes = []
        scene_id = 0
        scene_start = 0.0
        prev_frame = None
        prev_hist = None
        frame_idx = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                timestamp = frame_idx / fps
                
                # 每隔几帧检测一次 (节省计算)
                if frame_idx % 3 != 0:
                    frame_idx += 1
                    continue
                
                curr_hist = self.calculate_color_histogram(frame)
                
                if prev_hist is not None:
                    # 计算直方图差异
                    diff = np.mean(np.abs(curr_hist - prev_hist))
                    
                    # 检测场景切换
                    if diff > self._threshold / 100.0:
                        duration = timestamp - scene_start
                        if duration >= self._min_scene_duration:
                            scenes.append(SceneInfo(
                                scene_id=scene_id,
                                start_time=round(scene_start, 2),
                                end_time=round(timestamp, 2),
                                description=f"场景 {scene_id + 1}",
                                tags=[],
                                key_frame_index=frame_idx,
                            ))
                            scene_id += 1
                            scene_start = timestamp
                
                prev_hist = curr_hist
                frame_idx += 1
        finally:
            cap.release()
        
        # 添加最后一个场景
        if frame_idx > 0:
            scenes.append(SceneInfo(
                scene_id=scene_id,
                start_time=round(scene_start, 2),
                end_time=round(frame_idx / fps, 2),
                description=f"场景 {scene_id + 1}",
                tags=[],
                key_frame_index=frame_idx - 1,
            ))
        
        logger.info(f"检测到 {len(scenes)} 个场景")
        return scenes

    async def detect_scenes_async(
        self,
        video_path: str,
        fps: float = 30.0,
    ) -> list[SceneInfo]:
        """异步版本"""
        import asyncio
        
        def _detect():
            return self.detect_scenes(video_path, fps)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _detect)
