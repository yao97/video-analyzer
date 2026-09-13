# coding=utf-8
"""针对性复现验证：clip4(大唐芙蓉园) 的「西安曲江」易错点
- 无 context 跑 N 次、有 context 跑 N 次，统计「西安曲江」(正确) vs 「仙曲江/...曲江」(错误) 出现次数
- 验证 context 是否降低此类低频专有名词错误，以及模型随机性幅度
"""
import os, sys, re
SRC_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_gguf_src"
MODEL_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_models"
FFMPEG_BIN = r"D:\alist\ffmpeg_extract\ffmpeg-master-latest-win64-gpl-shared\bin"
sys.path.insert(0, SRC_DIR)
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")
from qwen_asr_gguf.inference import QwenASREngine, ASREngineConfig
import run_full_transcribe as R

CLIP = r"D:\_asr_test\clip4.m4a"
CTX = R.STREAMERS["大唐芙蓉园"]
N = 3

cfg = ASREngineConfig(model_dir=MODEL_DIR,
    encoder_frontend_fn="qwen3_asr_encoder_frontend.int4.onnx",
    encoder_backend_fn="qwen3_asr_encoder_backend.int4.onnx",
    llm_fn="qwen3_asr_llm.q4_k.gguf",
    onnx_provider="CPU", llm_use_gpu=True, enable_aligner=False, verbose=False)
engine = QwenASREngine(config=cfg)

def has_correct(t):  # 含「西安曲江」且无「仙曲江」
    return ("西安曲江" in t) and ("仙曲江" not in t)
def err_word(t):
    m = re.search(r"([\u4e00-\u9fff]{1,2})曲江", t)
    return m.group(1) + "曲江" if m else "(无曲江)"

print(f"=== 无 context × {N} ===")
no_correct = 0
for i in range(N):
    t = engine.transcribe(audio_file=CLIP, language="Chinese", context="", start_second=0.0, duration=None).text or ""
    ok = has_correct(t)
    no_correct += ok
    print(f"  [{i+1}] {'✅' if ok else '❌'} {err_word(t)}  | {t[:50]}")
print(f"  无context 正确率: {no_correct}/{N}")

print(f"=== 有 context × {N} ===")
with_correct = 0
for i in range(N):
    t = engine.transcribe(audio_file=CLIP, language="Chinese", context=CTX, start_second=0.0, duration=None).text or ""
    ok = has_correct(t)
    with_correct += ok
    print(f"  [{i+1}] {'✅' if ok else '❌'} {err_word(t)}  | {t[:50]}")
print(f"  有context 正确率: {with_correct}/{N}")

print(f"\n>>> 结论：无context {no_correct}/{N} vs 有context {with_correct}/{N} （西安曲江正确率）")
engine.shutdown()
