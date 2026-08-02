"""
音频分析器
使用 Whisper 进行语音识别 + librosa 进行音频特征分析
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from loguru import logger

from ..schemas.video_analysis import AudioAnalysis, AudioSegment


class AudioAnalyzer:
    """
    音频分析器
    能力:
    - 语音识别 (Whisper)
    - 音频特征提取 (librosa)
    - 语速分析
    - 情感倾向 (基础)
    """

    def __init__(self, model_size: str = "base"):
        """
        Args:
            model_size: Whisper 模型大小
            - tiny: ~39M, 最快, 最低精度
            - base: ~74M, 快速, 良好精度
            - small: ~244M, 中等速度, 较高精度
            - medium: ~769M, 较慢, 高精度
            - large: ~1550M, 最慢, 最高精度
        """
        self._model_size = model_size
        self._whisper_model = None

    def _load_whisper(self):
        """延迟加载 Whisper 模型"""
        if self._whisper_model is None:
            logger.info(f"加载 Whisper {self._model_size} 模型...")
            import whisper
            self._whisper_model = whisper.load_model(self._model_size)
            logger.info("Whisper 模型加载完成")

    async def transcribe_audio(self, video_path: str, language: str = "auto") -> dict:
        """
        使用 Whisper 进行语音转录
        
        Returns:
            Whisper 转录结果字典
        """
        self._load_whisper()
        
        # Whisper 推理是同步的,放到线程池执行
        loop = asyncio.get_event_loop()
        
        def _transcribe():
            import whisper
            # 确保模型已加载
            if self._whisper_model is None:
                self._whisper_model = whisper.load_model(self._model_size)
            
            result = self._whisper_model.transcribe(
                video_path,
                language=language if language != "auto" else None,
                verbose=False,
                task="transcribe",
            )
            return result
        
        result = await loop.run_in_executor(None, _transcribe)
        return result

    async def extract_audio_features(self, audio_path: str) -> dict:
        """
        使用 librosa 提取音频特征
        
        Returns:
            音频特征字典
        """
        loop = asyncio.get_event_loop()
        
        def _extract():
            import librosa
            import numpy as np
            
            # 加载音频
            y, sr = librosa.load(audio_path, sr=16000)  # 重采样到 16kHz
            
            # 提取各种特征
            features = {}
            
            # 1. 音高 (Pitch)
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_mean = float(np.mean(pitches[pitches > 0])) if np.any(pitches > 0) else 0
            features["pitch_hz"] = round(pitch_mean, 2)
            
            # 2. 能量/响度
            rms = librosa.feature.rms(y=y)
            features["energy"] = round(float(np.mean(rms)), 4)
            
            # 3. 语速估计 (基于音节检测)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo, _ = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)
            features["estimated_tempo"] = round(float(tempo), 2)
            
            # 4. 静音检测
            frame_length = 2048
            hop_length = 512
            non_silent = librosa.effects.split(
                y, top_db=20, frame_length=frame_length, hop_length=hop_length
            )
            total_frames = len(y) // hop_length
            non_silent_frames = sum(
                (end - start) for start, end in non_silent
            )
            speech_ratio = non_silent_frames / total_frames if total_frames > 0 else 0
            features["speech_ratio"] = round(speech_ratio, 4)
            
            # 5. 频谱特征 (MFCC)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            features["mfcc_mean"] = [round(float(np.mean(m)), 2) for m in mfccs]
            
            # 6. 频谱质心 (音色明亮度)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
            features["spectral_centroid"] = round(float(np.mean(spectral_centroids)), 2)
            
            return features
        
        features = await loop.run_in_executor(None, _extract)
        return features

    async def analyze_audio(
        self,
        video_path: str,
        language: str = "auto",
    ) -> AudioAnalysis:
        """综合音频分析"""
        
        # 检查是否有音频流
        has_audio = await self._check_audio_stream(video_path)
        if not has_audio:
            return AudioAnalysis(
                transcript="",
                language=None,
                language_confidence=0.0,
                segments=[],
                duration_seconds=0.0,
                has_speech=False,
                speech_ratio=0.0,
                energy_level=0.0,
            )
        
        # 提取音频文件路径
        audio_path = await self._extract_audio(video_path)
        
        try:
            # 并行执行转录和特征提取
            transcript_task = self.transcribe_audio(video_path, language)
            features_task = self.extract_audio_features(audio_path)
            
            transcript_result, features = await asyncio.gather(
                transcript_task, features_task
            )
            
            # 解析转录结果
            segments = []
            for seg in transcript_result.get("segments", []):
                segments.append(AudioSegment(
                    start_time=round(seg["start"], 2),
                    end_time=round(seg["end"], 2),
                    text=seg["text"].strip(),
                    language=transcript_result.get("language"),
                    confidence=round(seg.get("probability", 0.9), 3),
                ))
            
            # 组装完整文本
            full_text = " ".join(s["text"] for s in segments)
            
            return AudioAnalysis(
                transcript=full_text,
                language=transcript_result.get("language"),
                language_confidence=round(transcript_result.get("language", {}).get("confidence", 0), 3),
                segments=segments,
                duration_seconds=transcript_result.get("duration", 0),
                has_speech=len(segments) > 0,
                speech_ratio=features.get("speech_ratio", 0),
                energy_level=features.get("energy", 0),
            )
        finally:
            # 清理临时音频文件
            if audio_path and Path(audio_path).exists():
                try:
                    Path(audio_path).unlink()
                except Exception:
                    pass

    async def _check_audio_stream(self, video_path: str) -> bool:
        """检查视频是否有音频流"""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            video_path,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "audio" in result.stdout.lower()
        except Exception:
            return True  # 无法检测,假设有音频

    async def _extract_audio(self, video_path: str) -> str:
        """提取音频为临时 WAV 文件"""
        import tempfile
        
        audio_path = Path(tempfile.gettempdir()) / f"audio_{Path(video_path).stem}.wav"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",  # 不要视频
            "-acodec", "pcm_s16le",  # WAV 格式
            "-ar", "16000",  # 16kHz
            "-ac", "1",  # 单声道
            str(audio_path),
        ]
        
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
            )
        except Exception as e:
            logger.warning(f"音频提取失败: {e}")
            return ""
        
        return str(audio_path)
