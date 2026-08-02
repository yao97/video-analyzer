"""
画面分析器
使用 Vision Transformer + YOLO 进行画面内容分析
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional
from loguru import logger

from ..schemas.video_analysis import FrameAnalysis, DetectedObject


class FrameAnalyzer:
    """
    画面帧分析器
    能力:
    - 物体检测 (YOLO)
    - 场景识别 (CLIP/Vision Transformer)
    - 颜色分析
    - 运动检测
    """

    def __init__(self, use_gpu: bool = True):
        self._use_gpu = use_gpu
        self._yolo_model = None
        self._clip_model = None
        self._vision_model = None
        self._prev_frame: Optional[np.ndarray] = None

    def _load_yolo(self):
        """加载 YOLO 模型 (延迟加载)"""
        if self._yolo_model is None:
            logger.info("加载 YOLO 模型...")
            # 使用 ultralytics YOLO
            try:
                from ultralytics import YOLO
                self._yolo_model = YOLO("yolov8n.pt")  # nano 版本,最快
                logger.info("YOLO 模型加载完成")
            except ImportError:
                logger.warning("YOLO 未安装,使用 OpenCV 备选方案")
                self._yolo_model = "fallback"

    def _load_vision_model(self):
        """加载 Vision Transformer 用于场景描述"""
        if self._vision_model is None:
            logger.info("加载 Vision Transformer 模型...")
            try:
                from transformers import AutoImageProcessor, AutoModelForImageClassification
                import torch
                
                # 使用 google/vit-base-patch16-224
                self._vision_processor = AutoImageProcessor.from_pretrained(
                    "google/vit-base-patch16-224"
                )
                self._vision_model = AutoModelForImageClassification.from_pretrained(
                    "google/vit-base-patch16-224"
                )
                self._device = "cuda" if torch.cuda.is_available() and self._use_gpu else "cpu"
                self._vision_model.to(self._device)
                logger.info(f"Vision Transformer 加载完成, 设备: {self._device}")
            except Exception as e:
                logger.warning(f"Vision Transformer 加载失败: {e}, 使用备选方案")
                self._vision_model = "fallback"

    async def detect_objects(self, frame: np.ndarray) -> list[DetectedObject]:
        """检测画面中的物体"""
        self._load_yolo()
        
        if self._yolo_model == "fallback":
            return self._simple_object_detection(frame)
        
        # YOLO 推理
        results = self._yolo_model(frame, verbose=False)
        
        objects = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    conf = float(box.conf[0])
                    if conf < 0.3:  # 过滤低置信度
                        continue
                    cls_id = int(box.cls[0])
                    label = self._yolo_model.names[cls_id]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    objects.append(DetectedObject(
                        label=label,
                        confidence=round(conf, 3),
                        bbox=(x1, y1, x2, y2),
                    ))
        
        return objects

    async def describe_scene(self, frame: np.ndarray) -> tuple[str, list[str]]:
        """
        描述场景内容
        返回: (场景描述, 关键词标签列表)
        """
        self._load_vision_model()
        
        if self._vision_model == "fallback":
            return self._simple_scene_description(frame)
        
        # 使用 Vision Transformer 进行分类
        import torch
        from transformers import AutoImageProcessor
        
        inputs = self._vision_processor(images=frame, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self._vision_model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            top_prob, top_idx = torch.topk(probs, k=5, dim=-1)
        
        # 获取标签
        labels = self._vision_model.config.id2label
        tags = []
        descriptions = []
        
        for i, (prob, idx) in enumerate(zip(top_prob[0], top_idx[0])):
            if prob.item() > 0.05:  # 只取置信度 > 5% 的
                label = labels[idx.item()]
                tags.append(label)
                descriptions.append(f"{label} ({prob.item():.1%})")
        
        return "、".join(descriptions[:3]) if descriptions else "未知场景", tags[:5]

    def extract_dominant_colors(self, frame: np.ndarray, num_colors: int = 5) -> list[str]:
        """提取主色调"""
        # 压缩图像以加速处理
        small = cv2.resize(frame, (100, 100))
        
        # 转换为 RGB
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        
        # 使用 K-Means 聚类
        pixels = rgb.reshape(-1, 3).astype(np.float32)
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )
        
        # 转换为颜色名称
        colors = []
        for center in centers.astype(np.uint8):
            colors.append(self._rgb_to_color_name(center))
        
        return colors

    def calculate_motion(self, frame: np.ndarray) -> float:
        """计算运动强度 (0-1)"""
        if self._prev_frame is None:
            self._prev_frame = frame.copy()
            return 0.0
        
        # 转灰度
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(self._prev_frame, cv2.COLOR_BGR2GRAY)
        
        # 计算光流
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        
        # 计算平均运动幅度
        magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
        max_mag = np.max(magnitude)
        
        # 归一化
        motion = min(1.0, max_mag / 30.0)  # 假设 30 像素为最大运动
        
        self._prev_frame = frame.copy()
        return round(motion, 3)

    async def analyze_frame(
        self,
        frame: np.ndarray,
        frame_index: int,
        timestamp: float,
    ) -> FrameAnalysis:
        """综合分析单帧"""
        # 并行执行各分析任务
        import asyncio
        
        # 物体检测
        objects = await self.detect_objects(frame)
        
        # 场景描述
        scene_desc, tags = await self.describe_scene(frame)
        
        # 颜色分析
        colors = self.extract_dominant_colors(frame)
        
        # 运动强度
        motion = self.calculate_motion(frame)
        
        return FrameAnalysis(
            frame_index=frame_index,
            timestamp=round(timestamp, 2),
            scene_description=scene_desc,
            detected_objects=objects,
            dominant_colors=colors,
            motion_intensity=motion,
        )

    def _simple_object_detection(self, frame: np.ndarray) -> list[DetectedObject]:
        """简单的物体检测备选方案"""
        import cv2
        try:
            # 尝试使用 OpenCV 内置的 Haar Cascade
            if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                objects = []
                for (x, y, w, h) in faces:
                    objects.append(DetectedObject(
                        label="face",
                        confidence=0.7,
                        bbox=(x, y, x + w, y + h),
                    ))
                return objects
            else:
                # headless 版本无 cascade，直接返回
                return []
        except Exception:
            return []

    def _simple_scene_description(self, frame: np.ndarray) -> tuple[str, list[str]]:
        """简单的场景描述备选方案"""
        # 基于颜色和亮度做简单判断
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        avg_hue = np.mean(hsv[:, :, 0])
        avg_sat = np.mean(hsv[:, :, 1])
        avg_val = np.mean(hsv[:, :, 2])
        
        # 简单场景分类
        if avg_val < 50:
            return "暗光场景", ["dark", "indoor"]
        elif avg_val > 200:
            return "明亮场景", ["bright", "outdoor"]
        elif avg_sat > 150:
            return "色彩丰富场景", ["colorful", "vivid"]
        else:
            return "普通场景", ["normal", "neutral"]

    @staticmethod
    def _rgb_to_color_name(rgb: np.ndarray) -> str:
        """RGB 转颜色名称"""
        r, g, b = rgb
        
        # 简化判断
        if r > 200 and g < 100 and b < 100:
            return "红色"
        elif r > 200 and g > 200 and b < 100:
            return "黄色"
        elif r < 100 and g > 200 and b < 100:
            return "绿色"
        elif r < 100 and g < 100 and b > 200:
            return "蓝色"
        elif r > 200 and g > 200 and b > 200:
            return "白色"
        elif r < 50 and g < 50 and b < 50:
            return "黑色"
        elif r > 150 and g < 100 and b > 150:
            return "紫色"
        elif r > 200 and g > 150 and b < 100:
            return "橙色"
        else:
            return "灰色"
