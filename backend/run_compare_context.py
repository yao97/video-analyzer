# coding=utf-8
"""
术语表降字错率验证：同一音频片段，无 context vs 有术语表 context 两版转录对比
- 复用已抽好的稳定 clips（D:\_asr_test\clip1-5.m4a），不重新抽 mp4，不依赖正在变动的 m4a 拆分件
- 用 GPU(llm_use_gpu=True) 跑两版，统计术语命中增量 + 字符改动率 + 典型修正
- 产出：D:\_asr_test\compare\{clip}_noctx.txt / _withctx.txt、compare.json、compare_report.html
"""
import os, sys, time, json
SRC_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_gguf_src"
MODEL_DIR = r"C:\Users\EDY\Projects\video-analyzer\backend\qwen3_asr_models"
FFMPEG_BIN = r"D:\alist\ffmpeg_extract\ffmpeg-master-latest-win64-gpl-shared\bin"
CLIP_DIR = r"D:\_asr_test"
OUT = r"D:\_asr_test\compare"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, SRC_DIR)
os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")
from qwen_asr_gguf.inference import QwenASREngine, ASREngineConfig
import run_full_transcribe as R   # 复用 STREAMERS 上下文词串

CLIPS = {
    "clip1.m4a": "大唐芙蓉园",
    "clip2.m4a": "七峰山宠粉号-男团",
    "clip3.m4a": "奇幻天宫七峰山",
    "clip4.m4a": "大唐芙蓉园",
    "clip5.m4a": "滨州海底世界",
}

def lev(a, b):
    la, lb = len(a), len(b)
    if la == 0: return lb
    if lb == 0: return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0]*lb
        for j in range(1, lb + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            cur[j] = min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + cost)
        prev = cur
    return prev[lb]

def count_terms(text, terms):
    return sum(text.count(t) for t in terms)

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

report = {}
for clip, streamer in CLIPS.items():
    path = os.path.join(CLIP_DIR, clip)
    ctx = R.STREAMERS[streamer]
    ctx_terms = [w for w in ctx.replace("  ", " ").split() if len(w) >= 2]
    print(f"\n### {clip} [{streamer}]  context词数={len(ctx_terms)}")
    # 无 context
    t1 = time.time()
    r0 = engine.transcribe(audio_file=path, language="Chinese", context="", start_second=0.0, duration=None)
    no_ctx = r0.text or ""
    t_no = time.time() - t1
    # 有 context
    t2 = time.time()
    r1 = engine.transcribe(audio_file=path, language="Chinese", context=ctx, start_second=0.0, duration=None)
    with_ctx = r1.text or ""
    t_with = time.time() - t2
    # 统计
    c_no = count_terms(no_ctx, ctx_terms)
    c_with = count_terms(with_ctx, ctx_terms)
    new_hit = [w for w in ctx_terms if with_ctx.count(w) > no_ctx.count(w)]
    edit = lev(no_ctx, with_ctx)
    edit_rate = edit / max(len(no_ctx), 1)
    report[clip] = {
        "streamer": streamer,
        "ctx_terms": len(ctx_terms),
        "no_ctx_chars": len(no_ctx),
        "with_ctx_chars": len(with_ctx),
        "term_hit_no_ctx": c_no,
        "term_hit_with_ctx": c_with,
        "term_hit_delta": c_with - c_no,
        "new_hit_terms": new_hit,
        "edit_distance": edit,
        "edit_rate": round(edit_rate, 4),
        "time_no_ctx": round(t_no, 2),
        "time_with_ctx": round(t_with, 2),
    }
    with open(os.path.join(OUT, clip.replace(".m4a", "_noctx.txt")), "w", encoding="utf-8") as f:
        f.write(no_ctx)
    with open(os.path.join(OUT, clip.replace(".m4a", "_withctx.txt")), "w", encoding="utf-8") as f:
        f.write(with_ctx)
    print(f"  无ctx:{len(no_ctx)}字 命中{c_no} | 有ctx:{len(with_ctx)}字 命中{c_with} (+{c_with-c_no}) | 编辑距离{edit} 改动率{edit_rate:.3f}")
    print(f"  新增命中词: {new_hit[:15]}")

with open(os.path.join(OUT, "compare.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

# ---- HTML 报告 ----
html = ["<html><head><meta charset='utf-8'><title>术语表降字错率验证</title>",
        "<style>body{font-family:-apple-system,'Microsoft YaHei',sans-serif;background:#f6f7fb;color:#1f2329;margin:0;padding:24px}"
        "h1{font-size:22px}h2{font-size:17px;color:#2456e8;margin-top:24px}"
        ".card{background:#fff;border-radius:12px;padding:16px 20px;margin:14px 0;box-shadow:0 1px 4px rgba(0,0,0,.08)}"
        ".kv{font-size:13px;color:#5a6068;line-height:1.9}.hl{color:#0a7a3d;font-weight:700}"
        ".warn{color:#c0392b}.box{background:#f3f5fa;border-radius:8px;padding:10px 14px;margin:8px 0;font-size:13px;white-space:pre-wrap;line-height:1.7}"
        "table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}"
        "th,td{border:1px solid #e3e6eb;padding:6px 10px;text-align:left}"
        ".good{color:#0a7a3d;font-weight:700}.bar{display:inline-block;height:8px;background:#2456e8;border-radius:4px;vertical-align:middle}</style></head><body>"]
html.append("<h1>术语表降字错率验证报告（Qwen3-ASR-1.7B · 本地 GPU）</h1>")
html.append("<div class='card'><div class='kv'>验证方法：同一音频片段分别用 <b>无 context</b> 与 <b>有该主播术语表 context</b> 转录，对比术语命中增量与字符级改动率。<br>"
            "数据来源：D:\\_asr_test 下 5 个稳定短片段（clip1-5，各约 40s），不依赖正在变动的 m4a 拆分件。<br>"
            "注：严格字错率(CER)需人工校对参考文本，本验证以「术语命中增量 + 字符编辑距离」作为降错效果的代理指标。</div></div>")
# 汇总表
html.append("<h2>汇总对比</h2><div class='card'><table><tr><th>片段</th><th>主播</th><th>无ctx命中</th><th>有ctx命中</th><th>命中增量</th><th>编辑距离</th><th>改动率</th></tr>")
for clip, d in report.items():
    html.append(f"<tr><td>{clip}</td><td>{d['streamer']}</td><td>{d['term_hit_no_ctx']}</td>"
                f"<td>{d['term_hit_with_ctx']}</td><td class='good'>+{d['term_hit_delta']}</td>"
                f"<td>{d['edit_distance']}</td><td>{d['edit_rate']:.3f}</td></tr>")
html.append("</table></div>")
# 逐片段
for clip, d in report.items():
    html.append(f"<h2>{clip} · {d['streamer']}</h2><div class='card'>")
    html.append(f"<div class='kv'>术语表词数 <b>{d['ctx_terms']}</b> ｜ 无ctx <b>{d['no_ctx_chars']}</b>字 命中{d['term_hit_no_ctx']} ｜ "
                f"有ctx <b>{d['with_ctx_chars']}</b>字 命中{d['term_hit_with_ctx']} ｜ "
                f"命中增量 <span class='hl'>+{d['term_hit_delta']}</span> ｜ 字符编辑距离 {d['edit_distance']}（改动率 {d['edit_rate']:.3f}）</div>")
    html.append(f"<div class='kv'>context 带来的新增命中词：<span class='hl'>{'、'.join(d['new_hit_terms'][:20]) or '（无新增）'}</span></div>")
    html.append(f"<div class='box'><b>无 context：</b>\n{(open(os.path.join(OUT, clip.replace('.m4a','_noctx.txt')),encoding='utf-8').read()[:400])}</div>")
    html.append(f"<div class='box'><b>有 context：</b>\n{(open(os.path.join(OUT, clip.replace('.m4a','_withctx.txt')),encoding='utf-8').read()[:400])}</div>")
    html.append("</div>")
html.append("</body></html>")
with open(os.path.join(OUT, "compare_report.html"), "w", encoding="utf-8") as f:
    f.write("\n".join(html))
print("\n>>> 验证完成，报告已写入", OUT)
engine.shutdown()
