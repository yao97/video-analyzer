# coding=utf-8
"""GPU 加速 + context 热词偏置 实测"""
import os, sys, time
SRC_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_gguf_src"
MODEL_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_models"
FFMPEG_BIN = r"D:\alist\ffmpeg_extract\ffmpeg-master-latest-win64-gpl-shared\bin"
sys.path.insert(0, SRC_DIR)
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")
from qwen_asr_gguf.inference import QwenASREngine, ASREngineConfig

CLIP3 = r"D:\_asr_test\clip3.m4a"   # 奇幻天宫七峰山 40s
CLIP4 = r"D:\_asr_test\clip4.m4a"   # 大唐芙蓉园 40s (含"仙曲江"误识)

def run(use_gpu, context, label, clips):
    cfg = ASREngineConfig(
        model_dir=MODEL_DIR,
        encoder_frontend_fn="qwen3_asr_encoder_frontend.int4.onnx",
        encoder_backend_fn="qwen3_asr_encoder_backend.int4.onnx",
        llm_fn="qwen3_asr_llm.q4_k.gguf",
        onnx_provider="CPU", llm_use_gpu=use_gpu,
        enable_aligner=False, verbose=False)
    t = time.time(); eng = QwenASREngine(config=cfg); load = time.time() - t
    print(f"\n[init {label}] {load:.2f}s  (use_gpu={use_gpu})")
    for name, p in clips:
        t0 = time.time()
        res = eng.transcribe(audio_file=p, language="Chinese",
                             context=context, start_second=0, duration=None)
        tot = time.time() - t0
        perf = res.performance or {}
        rtf = tot / 40.0
        print(f"{label} {name}: total={tot:.2f}s RTF={rtf:.3f} "
              f"prefill={perf.get('prefill_time',0):.2f}s decode={perf.get('decode_time',0):.2f}s")
        print(f"    TEXT: {res.text}")
    eng.shutdown()

# 1) GPU 加速实测（对比之前 CPU：clip3 total=24.64s / clip4 total=7.67s）
run(True, None, "GPU", [("clip3", CLIP3), ("clip4", CLIP4)])
# 2) context 热词偏置：把正确地名/景区词喂进去，看能否修掉 仙曲江->西安曲江
run(True, "西安曲江大唐芙蓉园官方直播间景区门票演艺", "GPU+CTX", [("clip4", CLIP4)])
