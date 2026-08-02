"""Build web_player_v3.html from the clean source web_player.html.

Plan B (see docs/项目优化建议.md, Bug #7):
    Regenerate web_player_v3.html from the clean source web_player.html plus
    the deep-analysis patch provenance recorded in fix_deep_analysis.py.

History / why this replaced the old builder:
    The previous builder extracted JS by hard-coded line ranges from a 6-tab
    web_player.html and concatenated a hard-coded 6-tab <body> that still
    referenced CONTENT_TYPE_RULES / chart.umd.min.js / tabOverview / tabCharts /
    tabStructure. That brittle pipeline silently reintroduced the GBK-mojibake
    corruption (Bug #7) and dropped the D1-D4 cuts and the deep-analysis +
    AbortController fixes (Bug #3 / Bug #11) every time it ran.

    The clean source web_player.html is now the single source of truth: a
    complete, mojibake-free, 4-tab HTML document that already embeds the
    deep-analysis feature and the AbortController cancel/timeout logic. This
    builder is therefore a deterministic, self-validating passthrough: it
    asserts the source still carries every required fix BEFORE emitting the
    output, so a broken source can never silently ship.
"""
import hashlib
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "web_player.html")
OUT = os.path.join(ROOT, "web_player_v3.html")
PATCH = os.path.join(ROOT, "fix_deep_analysis.py")

# Known GBK-mojibake markers that must NEVER appear in the output.
MOJIBAKE_MARKERS = ["鍩轰簬", "閫夋嫨", "鐭╁", "鎼灭兢", "榛樿", "鏈€", "鈹€"]

# Features the clean source MUST contain.
REQUIRED_PRESENT = [
    ("深度拆解Tab", 'id="tabDeepReport"'),
    ("Bug#11-AbortController", "AbortController"),
    ("D4-语音转写Tab", "switchTab(this,'tabSpeech')"),
    ("D4-帧预览Tab", "switchTab(this,'tabFrames')"),
    ("D4-完整报告Tab", "switchTab(this,'tabReport')"),
]

# Content that Plan B cut (D1/D2/D3) and must NOT be present.
FORBIDDEN_PRESENT = [
    ("D1-内容类型规则", "CONTENT_TYPE_RULES"),
    ("D2-图表库引用", "chart.umd.min.js"),
    ("D1-总览Tab", "switchTab(this,'tabOverview')"),
    ("D2-图表Tab", "switchTab(this,'tabCharts')"),
    ("D3-结构Tab", "switchTab(this,'tabStructure')"),
]


def main() -> int:
    if not os.path.exists(SRC):
        print(f"[FAIL] source missing: {SRC}")
        return 1
    patch_present = os.path.exists(PATCH)
    if not patch_present:
        print(f"[WARN] deep-analysis patch provenance missing: {PATCH}")

    with open(SRC, encoding="utf-8") as f:
        src = f.read()

    errors = []

    # 1) No mojibake (Bug #7 guard)
    for m in MOJIBAKE_MARKERS:
        if m in src:
            errors.append(f"mojibake marker found: {m!r}")

    # 2) Required features present (Bug #3 / Bug #11 / D4)
    for label, token in REQUIRED_PRESENT:
        if token not in src:
            errors.append(f"missing required: {label} ({token!r})")

    # 3) Cut content absent (D1/D2/D3)
    for label, token in FORBIDDEN_PRESENT:
        if token in src:
            errors.append(f"forbidden still present: {label} ({token!r})")

    # 4) Exactly 4 tabs (D4)
    tabs = re.findall(r"switchTab\(this,'(tab\w+)'\)", src)
    if len(tabs) != 4:
        errors.append(f"expected 4 tabs, found {len(tabs)}: {tabs}")

    if errors:
        print("[FAIL] source validation failed — build aborted:")
        for e in errors:
            print("  - " + e)
        return 1

    # Emit verbatim: deterministic and idempotent (output == source, byte-for-byte).
    # shutil.copyfile preserves the source bytes exactly (incl. line endings),
    # avoiding any CRLF<->LF translation that a text-mode open() would introduce.
    shutil.copyfile(SRC, OUT)

    out_bytes = open(OUT, "rb").read()
    digest = hashlib.sha256(out_bytes).hexdigest()[:16]
    size = len(out_bytes)
    print("[OK] web_player_v3.html regenerated")
    print(f"  size   : {size:,} bytes")
    print(f"  sha256 : {digest}")
    print(f"  tabs   : {', '.join(tabs)}")
    print(f"  patch  : {'present' if patch_present else 'MISSING'} ({os.path.basename(PATCH)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
