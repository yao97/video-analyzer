import os
import sys
import time
import numpy as np
import onnxruntime as ort
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.absolute()))

from qwen_asr_gguf.inference.encoder import QwenAudioEncoder

def test_device(device_id, device_name):
    print(f"\n==================================================")
    print(f" 开始测试: {device_name} (Device ID: {device_id})")
    print(f"==================================================")
    
    # 动态猴子补丁：为 ONNX Runtime 强行注入指定的 DML device_id
    original_init = ort.InferenceSession.__init__
    def patched_init(self, path_or_bytes, sess_options=None, providers=None, provider_options=None, **kwargs):
        if providers and 'DmlExecutionProvider' in providers:
            # 找到 DML 在 providers 中的索引
            idx = providers.index('DmlExecutionProvider')
            
            # 补齐 provider_options
            if provider_options is None:
                provider_options = [{} for _ in providers]
            elif len(provider_options) < len(providers):
                provider_options.extend([{} for _ in range(len(providers) - len(provider_options))])
            
            # 注入 device_id
            if provider_options[idx] is None:
                provider_options[idx] = {}
            provider_options[idx]['device_id'] = device_id
            print(provider_options)
            
        return original_init(self, path_or_bytes, sess_options=sess_options, providers=providers, provider_options=provider_options, **kwargs)
    
    # 应用补丁
    ort.InferenceSession.__init__ = patched_init
    
    model_dir = "model"
    try:
        t_load_start = time.time()
        print("  正在拉起模型和 Session (包含 5s 预热)...")
        encoder = QwenAudioEncoder(
            frontend_path=os.path.join(model_dir, "qwen3_asr_encoder_frontend.fp32.onnx"),
            backend_path=os.path.join(model_dir, "qwen3_asr_encoder_backend.fp32.onnx"),
            mel_filters_path=os.path.join(model_dir, "mel_filters.npy"),
            use_dml=True,
            warmup_sec=5.0,
            verbose=False
        )
        print(f"  模型载入及预热耗时: {time.time() - t_load_start:.2f} 秒")
        
        # 准备 40 秒的音频数据 (采样率 16000)
        audio_40s = np.random.randn(40 * 16000).astype(np.float32)
        
        # 循环测试 3 次，取平均值
        times = []
        for i in range(3):
            print(f"  正在运行第 {i+1}/3 次 (40s 音频编码) ...", end="", flush=True)
            _, elapsed = encoder.encode(audio_40s)
            times.append(elapsed)
            print(f" 耗时: {elapsed:.3f} 秒")
            
        avg_time = sum(times) / len(times)
        rtf = avg_time / 40.0
        print(f"\n✅ {device_name} 测试完成")
        print(f"📊 音频长度: 40.0 秒")
        print(f"📊 平均耗时: {avg_time:.3f} 秒")
        print(f"📊 RTF (实时率): {rtf:.5f} (越小越快)")
        
    except Exception as e:
        print(f"\n❌ 测试失败，可能是该设备 ID 不存在或不支持 DML运算。\n异常信息: {e}")
        
    finally:
        # 测试完毕必须恢复原有的方法，防止污染后续代码
        ort.InferenceSession.__init__ = original_init


def main():
    print("--- 准备测试 ASR Encoder (FP16) 在不同 GPU DirectML 下的性能 ---\n")
    
    # Windows 环境下，通常 ID=0 是性能最强的独立显卡，ID=1 是核显
    # 具体视任务管理器的 GPU 排号而定
    test_device(0, "GPU 0 (通常为独显，如 RTX 5050)")
    test_device(1, "GPU 1 (通常为核显，如 Intel / AMD Radeon)")

if __name__ == '__main__':
    main()
