# coding=utf-8
"""
直播音频转录流水线（仅识别独立音频文件，不处理 mp4）
- 遍历 D:\录屏 下各主播子目录
- 只采集独立音频（m4a/wav/mp3/flac/aac），跳过 mp4
- 过滤：跳过 0 字节/过小(<5MB)、.part 截断残件
- 每个有效音频用 GPU(llm_use_gpu=True) + 该主播术语 context 整段转录
- 按主播落盘 D:\_asr_test\transcripts\{主播}.txt，支持断点续跑
- 用法：python run_full_transcribe.py            # 全部
        python run_full_transcribe.py 七峰山宠粉号-男团   # 仅单个主播（验证用）
"""
import os, sys, time, subprocess

SRC_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_gguf_src"
MODEL_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_models"
FFMPEG_BIN = r"D:\alist\ffmpeg_extract\ffmpeg-master-latest-win64-gpl-shared\bin"
BASE = r"D:\录屏"
OUT = r"D:\_asr_test\transcripts"

sys.path.insert(0, SRC_DIR)
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")
from qwen_asr_gguf.inference import QwenASREngine, ASREngineConfig

# 基础术语（通用直播/景区词）+ 各主播专属种子词
BASE_GLOSS = ("西安曲江大唐芙蓉园官方直播间 七峰山 奇幻天宫 滨州海底世界 洹溯大邑商 "
              "5D电影 3D电影 4D电影 直播间 主播 家人们 公屏 门票 囤票 拍票 链接 "
              "一票全含 二次消费 隐形消费 预定 优惠 省钱 暑期 演艺 演出 宠粉 "
              "海洋馆 萌宠馆 游乐场 星空馆 剧场 前山看演艺后山看风景 大人 小朋友")

STREAMERS = {
    "七峰山宠粉号-男团": BASE_GLOSS + " 七峰山 宠粉 男团 演艺 演出 门票 链接 拍票",
    "大唐芙蓉园":        BASE_GLOSS + " 西安曲江 大唐芙蓉园 官方直播间 前山看演艺后山看风景 门票 链接",
    "奇幻天宫七峰山":    BASE_GLOSS + " 奇幻天宫 七峰山 5D电影 3D电影 4D电影 链接 演艺 演出",
    "滨州海底世界":      BASE_GLOSS + " 滨州海底世界 海洋馆 萌宠馆 游乐场 星空馆 剧场 一票全含 二次消费 隐形消费 公屏 拍票",
    "熊治面包 门店团购":  BASE_GLOSS + " 熊治面包 门店团购 团购 面包 现烤 优惠券 自提 门店",
}

FFPROBE = os.path.join(FFMPEG_BIN, "ffprobe.exe")

def get_duration(path):
    try:
        out = subprocess.check_output([FFPROBE, "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
            stderr=subprocess.STDOUT, timeout=60)
        return float(out.decode().strip())
    except Exception:
        return 0.0

AUDIO_EXTS = (".m4a", ".wav", ".mp3", ".flac", ".ogg", ".aac")
MIN_BYTES = 5 * 1024 * 1024
def collect_files(streamer):
    """收集该主播目录下『有效且已写完』的独立音频。
    - 仅音频扩展名（含用户拆出的 .part.m4a）
    - <5MB 视为 0 字节/损坏残件，跳过
    - 大小在 1.2s 内发生变化 → 仍在抽取中，跳过（避免转录半截音频）
    """
    sd = os.path.join(BASE, streamer)
    if not os.path.isdir(sd):
        return []
    files = []
    for f in sorted(os.listdir(sd)):
        fl = f.lower()
        if not fl.endswith(AUDIO_EXTS):
            continue
        p = os.path.join(sd, f)
        try:
            s1 = os.path.getsize(p)
        except OSError:
            continue
        if s1 < MIN_BYTES:
            continue
        time.sleep(1.2)
        try:
            s2 = os.path.getsize(p)
        except OSError:
            continue
        if s2 != s1:
            print(f"    [跳过] {f}: 仍在写入({s1/1024/1024:.1f}→{s2/1024/1024:.1f}MB)")
            continue
        files.append(p)
    return files

def is_degenerate(text, min_len=2):
    """检测模型在坏音频上的退化输出（单一短串反复循环）。"""
    if not text or len(text) < 40:
        return False
    # 统计连续 2~4 字片段的重复次数
    for n in (2, 3, 4):
        from collections import Counter
        c = Counter(text[i:i+n] for i in range(len(text) - n + 1))
        top, cnt = c.most_common(1)[0]
        if cnt >= 10 and cnt * n > len(text) * 0.4:
            return True
    return False

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    os.makedirs(OUT, exist_ok=True)
    cfg = ASREngineConfig(
        model_dir=MODEL_DIR,
        encoder_frontend_fn="qwen3_asr_encoder_frontend.int4.onnx",
        encoder_backend_fn="qwen3_asr_encoder_backend.int4.onnx",
        llm_fn="qwen3_asr_llm.q4_k.gguf",
        onnx_provider="CPU", llm_use_gpu=True,
        enable_aligner=False, verbose=False)
    print(">>> 初始化引擎(llm_use_gpu=True) ...")
    t0 = time.time(); engine = QwenASREngine(config=cfg)
    print(f">>> 引擎就绪, 耗时 {time.time()-t0:.1f}s")

    targets = {only: STREAMERS[only]} if only else STREAMERS
    # 预统计总文件数（按文件断点续跑，应对边拆边加）
    plan = {s: collect_files(s) for s in targets}
    total = sum(len(v) for v in plan.values())
    done = 0
    print(f">>> 待转录音频文件共 {total} 个\n")
    for streamer, ctx in targets.items():
        sdir = os.path.join(OUT, streamer)
        os.makedirs(sdir, exist_ok=True)
        files = plan[streamer]
        if not files:
            print(f"### 主播[{streamer}] 无有效音频，跳过")
            continue
        print(f"### 主播[{streamer}] 有效音频 {len(files)} 个")
        for f in files:
            done += 1
            name = os.path.basename(f)
            out_f = os.path.join(sdir, name + ".txt")
            if os.path.exists(out_f):
                print(f"  [{done}/{total}] 跳过(已存在) {name}")
                continue
            dur = get_duration(f)
            t1 = time.time()
            try:
                res = engine.transcribe(audio_file=f, language="Chinese",
                                        context=ctx, start_second=0.0, duration=None)
                txt = res.text or ""
                if is_degenerate(txt):
                    txt = f"[疑似损坏音频·模型输出退化]\n{txt[:300]}…"
            except Exception as e:
                txt = f"[转录失败: {e}]"
            cost = time.time() - t1
            flag = " ⚠退化" if txt.startswith("[疑似") else ""
            with open(out_f, "w", encoding="utf-8") as fo:
                fo.write(f"===== {name} (时长约{dur:.0f}s, 耗时{cost:.1f}s){flag} =====\n{txt}\n")
            print(f"  [{done}/{total}] {name}: {dur:.0f}s -> {cost:.1f}s, {len(txt)}字{flag}")
    engine.shutdown()
    print(f"\n>>> 全部完成。共 {total} 个文件，本次处理至第 {done} 个。")

if __name__ == "__main__":
    main()
