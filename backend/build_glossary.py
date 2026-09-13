# coding=utf-8
"""
各主播术语表抽取（基于本地 Qwen3-ASR 转录结果）
- 读取 D:\_asr_test\transcripts\{主播}\*.txt
- 用 jieba 词性+词频抽取各主播专属术语
- 叠加种子领域词（直播/景区/各主播专属）
- 产出：D:\_asr_test\glossary\{主播}_术语表.txt + glossary.json + 汇总 HTML
"""
import os, re, json
from collections import Counter
import jieba
import jieba.posseg as pseg

TRANS = r"D:\_asr_test\transcripts"
OUT = r"D:\_asr_test\glossary"
os.makedirs(OUT, exist_ok=True)

# 各主播种子领域词（与 run_full_transcribe.py 的 STREAMERS context 对齐）
BASE_SEED = ["直播间","主播","家人们","公屏","门票","囤票","拍票","链接","一票全含",
             "二次消费","隐形消费","预定","优惠","省钱","暑期","演艺","演出","宠粉",
             "海洋馆","萌宠馆","游乐场","星空馆","剧场","大人","小朋友","5D电影","3D电影","4D电影"]
SEED = {
    "七峰山宠粉号-男团": BASE_SEED + ["七峰山","宠粉","男团","演艺","演出","门票","链接","拍票"],
    "大唐芙蓉园":        BASE_SEED + ["西安曲江","大唐芙蓉园","官方直播间","前山看演艺后山看风景","门票","链接"],
    "奇幻天宫七峰山":    BASE_SEED + ["奇幻天宫","七峰山","5D电影","3D电影","4D电影","链接","演艺","演出"],
    "滨州海底世界":      BASE_SEED + ["滨州海底世界","海洋馆","萌宠馆","游乐场","星空馆","剧场","一票全含","二次消费","隐形消费","公屏","拍票"],
    "熊治面包 门店团购":  BASE_SEED + ["熊治面包","门店团购","团购","面包","现烤","优惠券","自提","门店"],
}

# 直播口语停用词（噪音）
STOP = set(("的 了 是 在 我 你 他 她 它 我们 你们 他们 这 那 这个 那个 啊 呀 吧 呢 吗 哦 哈 嗯 "
            "就 都 也 还 不 没 有 和 跟 给 对 把 被 让 到 上 下 里 中 后 前 说 看 听 想 知道 觉得 "
            "现在 今天 明天 然后 所以 因为 但是 如果 一下 一个 一些 什么 怎么 多少 哪里 哪 谁 啦 咯 嘞 "
            "诶 哎 喂 好 行 可以 需要 要 会 能 去 来 做 用 买 卖 点 多 少 大 小 新 老 个 们 这么 那么 "
            "咱们 自己 一直 已经 应该 可能 真的 特别 非常 比较 还是 就是 没有 不是 都是 还有 他们 你们").split())

HAN = re.compile(r"^[\u4e00-\u9fffA-Za-z0-9]+$")

def read_streamer_text(streamer):
    sd = os.path.join(TRANS, streamer)
    if not os.path.isdir(sd):
        return ""
    parts = []
    n_fail = 0
    for f in sorted(os.listdir(sd)):
        if not f.endswith(".txt"):
            continue
        txt = open(os.path.join(sd, f), encoding="utf-8").read()
        # 按音频块切分（===== 头部），剔除转录失败的块
        blocks = re.split(r"(?m)^=====.*=====\s*", txt)
        for b in blocks:
            b = b.strip()
            if not b:
                continue
            if b.startswith("[转录失败") or b.startswith("[疑似"):
                n_fail += 1
                continue
            parts.append(b)
    return "\n".join(parts), n_fail

def extract_terms(text, top=80):
    cnt = Counter()
    for w, flag in pseg.cut(text):
        w = w.strip()
        if not w or w in STOP or not HAN.match(w) or len(w) < 2:
            continue
        # 保留名词/专名/动名词/习语/简称
        if flag.startswith(("n", "nz", "nt", "ns", "nl", "ng", "nr", "vn", "i", "j", "x")):
            cnt[w] += 1
    return cnt

report = {}
for s in sorted(SEED):
    text, n_fail = read_streamer_text(s)
    if not text:
        print(f"### {s}: 无转录文本（有效 0，失败 {n_fail}），跳过")
        continue
    if n_fail:
        print(f"### {s}: 有效文本 {len(text)}字，已跳过 {n_fail} 个失败音频块")
    term_cnt = extract_terms(text)
    # 叠加种子词（保证领域词必出现）
    for w in SEED[s]:
        term_cnt[w] = term_cnt.get(w, 0) + 1
    top = term_cnt.most_common(80)
    # 纯数据词（去掉种子，看模型实际识别出的高频词）
    data_terms = [(w, c) for w, c in top if w not in set(SEED[s])]
    report[s] = {"chars": len(text), "terms": top, "data_terms": data_terms[:40]}
    with open(os.path.join(OUT, s + "_术语表.txt"), "w", encoding="utf-8") as fo:
        fo.write(f"# {s} 专属术语表\n# 来源：本地 Qwen3-ASR 转录 + jieba 词频/词性抽取（共 {len(text)} 字）\n\n")
        fo.write("## 种子领域词（必含）\n")
        fo.write("  ".join(SEED[s]) + "\n\n")
        fo.write("## 模型高频识别词（降字错率优化候选）\n")
        for w, c in data_terms[:40]:
            fo.write(f"{w}\t{c}\n")
    print(f"### {s}: {len(text)}字, 抽取 {len(top)} 个候选术语")

with open(os.path.join(OUT, "glossary.json"), "w", encoding="utf-8") as fo:
    json.dump(report, fo, ensure_ascii=False, indent=2)

# ---- 汇总 HTML ----
html = ["<html><head><meta charset='utf-8'><title>各主播术语表</title>",
        "<style>body{font-family:-apple-system,'Microsoft YaHei',sans-serif;background:#f6f7fb;color:#1f2329;margin:0;padding:24px}"
        "h1{font-size:22px}.card{background:#fff;border-radius:12px;padding:18px 22px;margin:16px 0;box-shadow:0 1px 4px rgba(0,0,0,.08)}"
        ".streamer{font-size:18px;font-weight:700;color:#2456e8;margin-bottom:6px}"
        ".meta{color:#8a9099;font-size:13px;margin-bottom:10px}"
        ".tags{line-height:2}.tag{display:inline-block;background:#eef2ff;color:#2456e8;border-radius:6px;padding:2px 9px;margin:3px 4px;font-size:13px}"
        ".seed{background:#fff4e6;color:#b25b00}.dt{background:#e8f8ee;color:#0a7a3d}"
        "table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}"
        "th,td{border:1px solid #e3e6eb;padding:6px 10px;text-align:left}.warn{color:#c0392b;font-weight:700}</style></head><body>"]
html.append("<h1>各主播专属术语表（Qwen3-ASR 本地识别）</h1>")
for s in sorted(report):
    r = report[s]
    seeds = set(SEED.get(s, []))
    html.append(f"<div class='card'><div class='streamer'>{s}</div>"
                f"<div class='meta'>转录 {r['chars']} 字 · 候选术语 {len(r['terms'])} 个</div>")
    html.append("<div class='tags'>")
    for w, c in r["terms"]:
        cls = "tag seed" if w in seeds else "tag dt"
        html.append(f"<span class='{cls}'>{w} {c}</span>")
    html.append("</div></div>")
html.append("</body></html>")
with open(os.path.join(OUT, "glossary_report.html"), "w", encoding="utf-8") as fo:
    fo.write("\n".join(html))
print(">>> 术语表已写入", OUT)
