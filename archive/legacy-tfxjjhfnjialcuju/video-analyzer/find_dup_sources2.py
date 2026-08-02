import re

# Replicate the build exactly and check where dups come from
fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

def block(s, e):
    return ''.join(lines[s-1:e-1])

COLOR_RGB       = block(498, 545)
CONTENT_RULES   = block(546, 679)
SCORE_FN        = block(680, 716)
DETECT_FN       = block(717, 727)
ANALYZE_FN      = block(728, 848)
SCENE_FN        = block(849, 860)
BUILD_PHASES_FN = block(861, 881)
GET_PHASE_FN    = block(1002, 1065)
CT_META         = block(1066, 1093)
PROCESS_FN      = block(1093, 1246)
RENDER_METRICS  = block(1250, 1260)
RENDER_OVERVIEW = block(1261, 1308)
RENDER_SPEECH_S = block(1308, 1324)
RENDER_SPEECH   = block(1324, 1375)
RENDER_FINAL    = block(1376, 1380)
RENDER_FRAMES   = block(1380, 1404)
DESTROY_CHARTS  = block(1405, 1409)
RENDER_CHARTS   = block(1410, 1464)
RENDER_STRUCT   = block(1465, 1520)
RENDER_REPORT_FN= block(1521, 1612)
GEN_SCRIPT_FN   = block(983, 1001)
TRANSCRIBE_JS   = block(897, 916)
POLL_JS         = block(918, 982)
DOWNLOAD_REPORT = block(1613, 1622)
DOWNLOAD_FRAMES = block(1623, 1634)
INIT_CODE       = block(1635, 1640)

# Assemble exactly as build does
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
    COLOR_RGB,
    CONTENT_RULES,
    SCORE_FN,
    DETECT_FN,
    ANALYZE_FN,
    SCENE_FN,
    BUILD_PHASES_FN,
    GET_PHASE_FN,
    CT_META,
    PROCESS_FN,
    GEN_SCRIPT_FN,
    RENDER_METRICS,
    RENDER_OVERVIEW,
    RENDER_SPEECH_S,
    RENDER_SPEECH,
    RENDER_FINAL,
    RENDER_FRAMES,
    DESTROY_CHARTS,
    RENDER_CHARTS,
    RENDER_STRUCT,
    RENDER_REPORT_FN,
    TRANSCRIBE_JS,
    POLL_JS,
    DOWNLOAD_REPORT,
    DOWNLOAD_FRAMES,
    INIT_CODE,
    "console.log('[v3] loaded');",
])

# Find where each function appears
for fn_name in ['processFile', 'renderSpeechSummary', 'renderSpeech', 'renderFrames']:
    pattern = r'function ' + fn_name if fn_name != 'processFile' else r'async function processFile'
    matches = [(m.start(), m.group()) for m in re.finditer(pattern, v3_script)]
    if len(matches) > 1:
        print(f"\n{fn_name} appears {len(matches)} times:")
        for pos, _ in matches:
            # Show what block this position falls in
            # Calculate cumulative position
            pass
        # Show which blocks contain each occurrence
        block_map = [
            ('COLOR_RGB', COLOR_RGB),
            ('CONTENT_RULES', CONTENT_RULES),
            ('SCORE_FN', SCORE_FN),
            ('DETECT_FN', DETECT_FN),
            ('ANALYZE_FN', ANALYZE_FN),
            ('SCENE_FN', SCENE_FN),
            ('BUILD_PHASES_FN', BUILD_PHASES_FN),
            ('GET_PHASE_FN', GET_PHASE_FN),
            ('CT_META', CT_META),
            ('PROCESS_FN', PROCESS_FN),
            ('GEN_SCRIPT_FN', GEN_SCRIPT_FN),
            ('RENDER_METRICS', RENDER_METRICS),
            ('RENDER_OVERVIEW', RENDER_OVERVIEW),
            ('RENDER_SPEECH_S', RENDER_SPEECH_S),
            ('RENDER_SPEECH', RENDER_SPEECH),
            ('RENDER_FINAL', RENDER_FINAL),
            ('RENDER_FRAMES', RENDER_FRAMES),
            ('DESTROY_CHARTS', DESTROY_CHARTS),
            ('RENDER_CHARTS', RENDER_CHARTS),
            ('RENDER_STRUCT', RENDER_STRUCT),
            ('RENDER_REPORT_FN', RENDER_REPORT_FN),
            ('TRANSCRIBE_JS', TRANSCRIBE_JS),
            ('POLL_JS', POLL_JS),
            ('DOWNLOAD_REPORT', DOWNLOAD_REPORT),
            ('DOWNLOAD_FRAMES', DOWNLOAD_FRAMES),
            ('INIT_CODE', INIT_CODE),
        ]
        for pos, _ in matches:
            cumulative = 0
            for name, content in block_map:
                if cumulative <= pos < cumulative + len(content):
                    print(f"  pos {pos}: inside {name}")
                    break
                cumulative += len(content) + 1  # +1 for newline from join
    else:
        print(f"\n{fn_name}: unique")
