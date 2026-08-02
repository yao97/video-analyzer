import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

def block(s, e):
    return ''.join(lines[s-1:e-1])

# Check blocks around renderSpeechSummary and renderFrames duplicates
# renderSpeechSummary at pos 30026 and 30060
# renderFrames at pos 33869 and 33897

# Build all blocks as in build_v3.py
blocks_def = [
    ('COLOR_RGB', 498, 545),
    ('CONTENT_RULES', 546, 679),
    ('SCORE_FN', 680, 716),
    ('DETECT_FN', 717, 727),
    ('ANALYZE_FN', 728, 848),
    ('SCENE_FN', 849, 860),
    ('BUILD_PHASES_FN', 861, 881),
    ('GET_PHASE_FN', 1002, 1065),
    ('CT_META', 1066, 1092),  # FIXED
    ('PROCESS_FN', 1093, 1246),
    ('RENDER_METRICS', 1250, 1260),
    ('RENDER_OVERVIEW', 1261, 1308),
    ('RENDER_SPEECH_S', 1308, 1323),
    ('RENDER_SPEECH', 1324, 1375),
    ('RENDER_FINAL', 1376, 1380),
    ('RENDER_FRAMES', 1380, 1404),
    ('DESTROY_CHARTS', 1405, 1409),
    ('RENDER_CHARTS', 1410, 1464),
    ('RENDER_STRUCT', 1465, 1520),
    ('RENDER_REPORT_FN', 1521, 1612),
    ('GEN_SCRIPT_FN', 983, 1001),
    ('TRANSCRIBE_JS', 897, 916),
    ('POLL_JS', 918, 982),
    ('DOWNLOAD_REPORT', 1613, 1622),
    ('DOWNLOAD_FRAMES', 1623, 1634),
    ('INIT_CODE', 1635, 1640),
]

blocks = {name: block(s, e) for name, s, e in blocks_def}

# Join in the same order as build
v3_script = '\n'.join([
    "// State",
    "let analysisResult = null;",
    "let speechResult = null;",
    "let frameImages = [];",
    "let chartRefs = {};",
    "let transcribeJobId = null;",
    "let transcribePollTimer = null;",
    "",
    "// Helpers",
    "const $ = id => document.getElementById(id);",
    "const show = id => $(id)?.classList.remove('hidden');",
    "const hide = id => $(id)?.classList.add('hidden');",
    "",
    "const toast = (msg, type='success') => {",
    "  const t = $('toast');",
    "  t.textContent = msg; t.className = 'toast ' + type + ' show';",
    "  setTimeout(() => t.classList.remove('show'), 3500);",
    "};",
    "",
    "const switchTab = (btn, pid) => {",
    "  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));",
    "  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));",
    "  btn.classList.add('active');",
    "  $(pid)?.classList.add('active');",
    "  if (pid === 'tabCharts') setTimeout(() => Object.values(chartRefs).forEach(c => c?.resize?.()), 80);",
    "};",
    "",
    blocks['COLOR_RGB'],
    blocks['CONTENT_RULES'],
    blocks['SCORE_FN'],
    blocks['DETECT_FN'],
    blocks['ANALYZE_FN'],
    blocks['SCENE_FN'],
    blocks['BUILD_PHASES_FN'],
    blocks['GET_PHASE_FN'],
    blocks['CT_META'],
    blocks['PROCESS_FN'],
    blocks['GEN_SCRIPT_FN'],
    blocks['RENDER_METRICS'],
    blocks['RENDER_OVERVIEW'],
    blocks['RENDER_SPEECH_S'],
    blocks['RENDER_SPEECH'],
    blocks['RENDER_FINAL'],
    blocks['RENDER_FRAMES'],
    blocks['DESTROY_CHARTS'],
    blocks['RENDER_CHARTS'],
    blocks['RENDER_STRUCT'],
    blocks['RENDER_REPORT_FN'],
    blocks['TRANSCRIBE_JS'],
    blocks['POLL_JS'],
    blocks['DOWNLOAD_REPORT'],
    blocks['DOWNLOAD_FRAMES'],
    blocks['INIT_CODE'],
    "console.log('[v3] loaded');",
])

# Find positions of duplicate occurrences
for fn_name in ['renderSpeechSummary', 'renderFrames']:
    pattern = r'function ' + fn_name
    matches = [(m.start(), m.end()) for m in re.finditer(pattern, v3_script)]
    if len(matches) > 1:
        print(f"\n{fn_name}: {len(matches)} occurrences at {[(s,e) for s,e in matches]}")
        for pos, _ in matches:
            # Which block?
            cumulative = 0
            sep_len = 1  # for '\n'.join
            for name, s, e in blocks_def:
                content = blocks[name]
                if cumulative <= pos < cumulative + len(content):
                    print(f"  pos {pos}: inside {name} (block starts at {cumulative})")
                    break
                cumulative += len(content) + sep_len
        # Show context
        for pos, _ in matches:
            ctx = v3_script[max(0,pos-60):pos+80]
            print(f"  pos {pos} ctx: {repr(ctx)}")
