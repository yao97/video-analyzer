"""测试 Whisper 能否直接处理 numpy 数组（不经过 ffmpeg）"""
import numpy as np, soundfile as sf, whisper, sys

print("加载 Whisper tiny 模型...")
model = whisper.load_model("tiny", device="cpu")
print("模型加载完成")

# 生成一个 3 秒的测试音频（440Hz 正弦波）
sr = 16000
t = np.linspace(0, 3, sr * 3, dtype=np.float32)
test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

print(f"测试音频: shape={test_audio.shape}, dtype={test_audio.dtype}")

# 测试直接传 numpy 数组
try:
    print("开始转写（直接传 numpy 数组）...")
    result = model.transcribe(test_audio, language="zh", task="transcribe", verbose=False, fp16=False)
    print(f"成功！转写结果: {result.get('text','')[:100]}")
except Exception as e:
    print(f"失败: {e}")
    import traceback
    traceback.print_exc()

# 对比：先写成 WAV 文件再转写
print("\n对比：写成 WAV 再转写...")
import tempfile, os
tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
tmppath = tmp.name
tmp.close()
sf.write(tmppath, test_audio, sr)
try:
    result2 = model.transcribe(tmppath, language="zh", task="transcribe", verbose=False, fp16=False)
    print(f"成功！转写结果: {result2.get('text','')[:100]}")
except Exception as e:
    print(f"失败: {e}")
os.unlink(tmppath)
