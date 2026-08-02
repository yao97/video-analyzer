import os
import sys
import pynvml
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.absolute()))

from qwen_asr_gguf.inference import llama
from qwen_asr_gguf.inference.encoder import QwenAudioEncoder

def get_vram():
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    return info.used / 1024**2 # MB

def main():
    print(f"--- 初始显存: {get_vram():.2f} MB ---")
    
    model_dir = "model"
    
    # 1. 载入 ASR Encoder
    print("\n[1/4] 载入 ASR Encoder...")
    vram_before = get_vram()
    asr_encoder = QwenAudioEncoder(
        frontend_path=os.path.join(model_dir, "qwen3_aligner_encoder_frontend.int4.onnx"),
        backend_path=os.path.join(model_dir, "qwen3_aligner_encoder_backend.int4.onnx"),
        mel_filters_path=os.path.join(model_dir, "mel_filters.npy"),
        use_dml=True,
        warmup_sec=40.0,
        verbose=False
    )
    vram_after = get_vram()
    print(f"--> ASR Encoder 载入完毕. 显存增量: {vram_after - vram_before:.2f} MB")
    print(f"--> 当前显存: {vram_after:.2f} MB")
    # 3. 载入 Aligner Encoder
    print("\n[3/4] 载入 Aligner Encoder...")
    vram_before = get_vram()
    aligner_encoder = QwenAudioEncoder(
        frontend_path=os.path.join(model_dir, "qwen3_aligner_encoder_frontend.int4.onnx"),
        backend_path=os.path.join(model_dir, "qwen3_aligner_encoder_backend.int4.onnx"),
        mel_filters_path=os.path.join(model_dir, "mel_filters.npy"),
        use_dml=True,
        warmup_sec=40.0,
        verbose=False
    )
    vram_after = get_vram()
    print(f"--> Aligner Encoder 载入完毕. 显存增量: {vram_after - vram_before:.2f} MB")
    print(f"--> 当前显存: {vram_after:.2f} MB")
    
    # 2. 载入 ASR Decoder
    print("\n[2/4] 载入 ASR Decoder...")
    vram_before = get_vram()
    asr_decoder_file = os.path.join(model_dir, "qwen3_asr_llm.q4_k.gguf")
    asr_model = llama.LlamaModel(asr_decoder_file)
    vram_after = get_vram()
    print(f"--> ASR Decoder 载入完毕. 显存增量: {vram_after - vram_before:.2f} MB")
    print(f"--> 当前显存: {vram_after:.2f} MB")

    vram_before = get_vram()
    asr_ctx = llama.LlamaContext(asr_model, n_ctx=2048, n_batch=8, embeddings=False)
    vram_after = get_vram()
    print(f"--> ASR Decoder Context 初始化完毕. 显存增量: {vram_after - vram_before:.2f} MB")
    print(f"--> 当前显存: {vram_after:.2f} MB")

    
    # 4. 载入 Aligner Decoder
    print("\n[4/4] 载入 Aligner Decoder...")
    vram_before = get_vram()
    aligner_decoder_file = os.path.join(model_dir, "qwen3_aligner_llm.q4_k.gguf")
    # Aligner Decoder 按照 aligner.py 中的写法，开启了 n_gpu_layers=-1
    aligner_model = llama.LlamaModel(aligner_decoder_file, n_gpu_layers=-1)
    vram_after = get_vram()
    print(f"--> Aligner Decoder 载入完毕. 显存增量: {vram_after - vram_before:.2f} MB")
    print(f"--> 当前显存: {vram_after:.2f} MB")


    vram_before = get_vram()
    aligner_ctx = llama.LlamaContext(aligner_model, n_ctx=2048, n_batch=8, embeddings=False)
    vram_after = get_vram()
    print(f"--> Aligner Decoder Context 初始化完毕. 显存增量: {vram_after - vram_before:.2f} MB")
    print(f"--> 当前显存: {vram_after:.2f} MB")
    
if __name__ == '__main__':
    main()
