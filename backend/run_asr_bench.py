# coding=utf-8
"""
Qwen3-ASR-1.7B 本地识别基准测试
- 引擎仅初始化一次，顺序转录多个片段
- 记录：音频时长、总耗时、RTF、编码器耗时、LLM 预填充/生成耗时、生成 token 数
- 输出文本 + JSON 汇总
"""
import os, sys, time, json, subprocess

SRC_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_gguf_src"
MODEL_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_models"
FFMPEG_BIN = r"D:\alist\ffmpeg_extract\ffmpeg-master-latest-win64-gpl-shared\bin"
FFPROBE = os.path.join(FFMPEG_BIN, "ffprobe.exe")

sys.path.insert(0, SRC_DIR)
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")

from qwen_asr_gguf.inference import QwenASREngine, ASREngineConfig

CLIPS = [
    ("clip1", r"D:\_asr_test\clip1.m4a", "大唐芙蓉园"),
    ("clip2", r"D:\_asr_test\clip2.m4a", "七峰山宠粉号-男团"),
    ("clip3", r"D:\_asr_test\clip3.m4a", "奇幻天宫七峰山"),
    ("clip4", r"D:\_asr_test\clip4.m4a", "大唐芙蓉园"),
    ("clip5", r"D:\_asr_test\clip5.m4a", "滨州海底世界"),
]

def get_duration(path):
    try:
        out = subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            stderr=subprocess.STDOUT)
        return float(out.decode().strip())
    except Exception as e:
        return None

def main():
    config = ASREngineConfig(
        model_dir=MODEL_DIR,
        encoder_frontend_fn="qwen3_asr_encoder_frontend.int4.onnx",
        encoder_backend_fn="qwen3_asr_encoder_backend.int4.onnx",
        llm_fn="qwen3_asr_llm.q4_k.gguf",
        onnx_provider="CPU",
        llm_use_gpu=False,
        enable_aligner=False,
        verbose=True,
    )
    t_load = time.time()
    engine = QwenASREngine(config=config)
    load_sec = time.time() - t_load
    print(f"\n##### 引擎初始化耗时: {load_sec:.2f} 秒 #####\n")

    rows = []
    for name, path, scene in CLIPS:
        dur = get_duration(path)
        t0 = time.time()
        res = engine.transcribe(audio_file=path, language="Chinese",
                                context=None, start_second=0, duration=None)
        t_total = time.time() - t0
        perf = res.performance or {}
        rtf = (t_total / dur) if dur else None
        gen_tok = perf.get("decode_tokens", 0)
        gen_t = perf.get("decode_time", 0.0)
        pre_tok = perf.get("prefill_tokens", 0)
        pre_t = perf.get("prefill_time", 0.0)
        enc_t = perf.get("encode_time", 0.0)
        gen_spd = (gen_tok / gen_t) if gen_t else 0
        pre_spd = (pre_tok / pre_t) if pre_t else 0
        n_chars = len(res.text)
        print(f"\n========== {name} [{scene}] ==========")
        print(f"音频时长={dur:.2f}s  总耗时={t_total:.2f}s  RTF={rtf:.3f}")
        print(f"字符数={n_chars}  生成tokens={gen_tok} ({gen_spd:.1f} tok/s)  预填充={pre_tok}tok ({pre_spd:.1f} tok/s)")
        print(f"--- 识别文本 ---\n{res.text}\n")
        rows.append({
            "name": name, "scene": scene, "audio_dur": round(dur, 2) if dur else None,
            "total_sec": round(t_total, 2), "rtf": round(rtf, 4) if rtf else None,
            "encode_sec": round(enc_t, 3),
            "prefill_sec": round(pre_t, 3), "prefill_tok": pre_tok, "prefill_tok_s": round(pre_spd, 1),
            "decode_sec": round(gen_t, 3), "decode_tok": gen_tok, "decode_tok_s": round(gen_spd, 1),
            "chars": n_chars, "text": res.text,
        })
        # 保存单条文本
        with open(os.path.join(r"D:\_asr_test", f"{name}.txt"), "w", encoding="utf-8") as f:
            f.write(res.text)

    engine.shutdown()

    summary = {
        "model": "Qwen3-ASR-1.7B (q4_k.gguf + int4.onnx)",
        "engine_init_sec": round(load_sec, 2),
        "device": "CPU (onnxruntime CPU + llama.cpp CPU)",
        "clips": rows,
    }
    with open(r"D:\_asr_test\asr_bench.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n##### 汇总已写入 D:\\_asr_test\\asr_bench.json #####")

if __name__ == "__main__":
    main()
