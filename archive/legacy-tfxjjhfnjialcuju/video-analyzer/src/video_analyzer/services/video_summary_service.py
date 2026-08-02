"""
视频总结服务
基于分析结果生成视频总结
"""
import asyncio
from typing import Optional
from loguru import logger

from ..schemas.video_analysis import (
    VideoMetadata,
    FrameAnalysis,
    AudioAnalysis,
    SceneInfo,
    VideoSummary,
)


class VideoSummaryService:
    """
    视频总结生成器
    基于多模态分析结果生成结构化总结
    """

    def __init__(self):
        self._llm_client = None  # 可扩展:接入 LLM API

    async def generate_summary(
        self,
        metadata: VideoMetadata,
        frame_analyses: list[FrameAnalysis],
        audio_analysis: Optional[AudioAnalysis],
        scenes: list[SceneInfo],
    ) -> VideoSummary:
        """生成视频总结"""
        
        # 1. 收集物体检测结果
        all_objects = []
        for frame in frame_analyses:
            all_objects.extend([obj.label for obj in frame.detected_objects])
        
        # 2. 统计高频物体
        object_counts: dict[str, int] = {}
        for obj in all_objects:
            object_counts[obj] = object_counts.get(obj, 0) + 1
        
        top_objects = sorted(object_counts.items(), key=lambda x: -x[1])[:10]
        
        # 3. 分析转录文本
        transcript_text = ""
        if audio_analysis:
            transcript_text = audio_analysis.transcript
        
        # 4. 简单关键词提取 (TF-IDF 简化版)
        keywords = self._extract_keywords(transcript_text, top_objects)
        
        # 5. 内容分类
        categories = self._classify_content(top_objects, metadata)
        
        # 6. 生成亮点
        highlights = self._generate_highlights(
            frame_analyses, audio_analysis, scenes
        )
        
        # 7. 情感分析 (简化)
        sentiment = self._analyze_sentiment(transcript_text)
        
        # 8. 标题和描述
        title = self._generate_title(top_objects, keywords)
        description = self._generate_description(
            metadata, categories, highlights, transcript_text
        )
        
        return VideoSummary(
            title=title,
            description=description,
            categories=categories,
            key_topics=keywords[:10],
            highlights=highlights,
            sentiment=sentiment,
            target_audience=None,
            content_warnings=[],  # 可扩展: 暴力/敏感内容检测
        )

    def _extract_keywords(
        self,
        transcript: str,
        top_objects: list[tuple[str, int]],
    ) -> list[str]:
        """提取关键词"""
        keywords = []
        
        # 添加检测到的物体
        keywords.extend([obj for obj, _ in top_objects[:5]])
        
        # 简单停用词
        stop_words = {
            "的", "是", "在", "有", "和", "了", "我", "你", "他", "她", "它",
            "这", "那", "都", "也", "要", "会", "可以", "这个", "那个",
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
        }
        
        if transcript:
            # 简单分词
            words = transcript.replace(",", " ").replace(".", " ").split()
            word_counts: dict[str, int] = {}
            for word in words:
                word_lower = word.lower().strip()
                if len(word_lower) > 2 and word_lower not in stop_words:
                    word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
            
            # 取高频词
            top_words = sorted(word_counts.items(), key=lambda x: -x[1])[:5]
            keywords.extend([w for w, _ in top_words])
        
        # 去重
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique_keywords.append(k)
        
        return unique_keywords[:15]

    def _classify_content(
        self,
        top_objects: list[tuple[str, int]],
        metadata: VideoMetadata,
    ) -> list[str]:
        """内容分类"""
        categories = []
        object_labels = {obj for obj, _ in top_objects}
        
        # 基于检测到的物体分类
        category_map = {
            "人物": ["person", "face", "man", "woman", "child", "people", "boy", "girl"],
            "动物": ["dog", "cat", "bird", "horse", "cow", "elephant", "bear", "zebra"],
            "食物": ["pizza", "cake", "apple", "banana", "food", "sandwich"],
            "交通工具": ["car", "bus", "truck", "bicycle", "motorcycle", "airplane", "train"],
            "户外风景": ["sky", "cloud", "mountain", "sea", "beach", "tree", "grass"],
            "室内场景": ["chair", "table", "couch", "bed", "window", "door"],
            "体育运动": ["sports", "ball", "tennis", "basketball", "football", "soccer"],
            "音乐": ["guitar", "piano", "microphone", "music"],
            "科技": ["laptop", "phone", "computer", "keyboard", "monitor", "tv"],
        }
        
        for category, labels in category_map.items():
            if any(label in object_labels for label in labels):
                categories.append(category)
        
        # 基于视频比例/尺寸辅助判断
        if metadata.width > 0 and metadata.height > 0:
            ratio = metadata.width / metadata.height
            if ratio > 1.7:
                categories.append("横屏视频")
            elif ratio < 0.8:
                categories.append("竖屏视频")
        
        return categories or ["其他"]

    def _generate_highlights(
        self,
        frame_analyses: list[FrameAnalysis],
        audio_analysis: Optional[AudioAnalysis],
        scenes: list[SceneInfo],
    ) -> list[str]:
        """生成亮点"""
        highlights = []
        
        # 基于场景数量
        if len(scenes) > 5:
            highlights.append(f"视频包含 {len(scenes)} 个不同场景")
        elif len(scenes) > 2:
            highlights.append(f"视频场景丰富,共 {len(scenes)} 个镜头")
        
        # 基于运动强度
        if frame_analyses:
            avg_motion = sum(f.motion_intensity for f in frame_analyses) / len(frame_analyses)
            if avg_motion > 0.5:
                highlights.append("视频节奏较快,画面活动频繁")
            elif avg_motion < 0.2:
                highlights.append("视频节奏平稳,画面相对静态")
        
        # 基于语音内容
        if audio_analysis and audio_analysis.has_speech:
            word_count = len(audio_analysis.transcript.split())
            highlights.append(f"包含语音解说,约 {word_count} 字")
        
        return highlights[:5]

    def _analyze_sentiment(self, text: str) -> str:
        """简单情感分析"""
        if not text:
            return "neutral"
        
        # 简化词典
        positive_words = {
            "好", "棒", "优秀", "喜欢", "开心", "快乐", "精彩", "完美",
            "good", "great", "excellent", "amazing", "love", "happy", "wonderful",
        }
        negative_words = {
            "差", "糟糕", "讨厌", "失望", "无聊", "垃圾", "坏",
            "bad", "terrible", "awful", "hate", "sad", "boring", "worst",
        }
        
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"

    def _generate_title(
        self,
        top_objects: list[tuple[str, int]],
        keywords: list[str],
    ) -> str:
        """生成标题"""
        if top_objects:
            main_subject = top_objects[0][0]
            return f"关于{main_subject}的视频"
        elif keywords:
            return f"主题: {keywords[0]}"
        else:
            return "视频内容分析"

    def _generate_description(
        self,
        metadata: VideoMetadata,
        categories: list[str],
        highlights: list[str],
        transcript: str,
    ) -> str:
        """生成描述"""
        parts = []
        
        # 基本信息
        parts.append(f"视频时长 {metadata.duration_seconds:.1f} 秒")
        parts.append(f"分辨率 {metadata.width}x{metadata.height}")
        
        # 分类
        if categories:
            parts.append(f"内容分类: {'/'.join(categories[:3])}")
        
        # 亮点
        if highlights:
            parts.append("主要特点: " + " ".join(highlights[:2]))
        
        return " | ".join(parts)
