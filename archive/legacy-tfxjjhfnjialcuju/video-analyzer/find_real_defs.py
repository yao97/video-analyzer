import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Real function definitions (at column 0, not inside template literals)
def find_real_defs(text):
    """Find function definitions at the start of a line (not inside template literals)"""
    result = []
    in_template = 0
    for i, line in enumerate(text.split('\n')):
        stripped = line.lstrip()
        is_def = stripped.startswith('function ') or stripped.startswith('async function ')
        # Simple heuristic: if template depth changed, be careful
        # Actually just check if the line STARTS with function keyword (column 0 after strip)
        if is_def:
            result.append((i+1, stripped[:60]))
    return result

# Check all blocks for real definitions
all_blocks = [
    ('COLOR_RGB', 498, 545),
    ('CONTENT_RULES', 546, 679),
    ('SCORE_FN', 680, 716),
    ('DETECT_FN', 717, 727),
    ('ANALYZE_FN', 728, 848),
    ('SCENE_FN', 849, 860),
    ('BUILD_PHASES_FN', 861, 881),
    ('GET_PHASE_FN', 1002, 1065),
    ('CT_META', 1066, 1093),
    ('PROCESS_FN', 1093, 1246),
    ('RENDER_METRICS', 1250, 1260),
    ('RENDER_OVERVIEW', 1261, 1308),
    ('RENDER_SPEECH_S', 1308, 1324),
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

target = ['processFile', 'renderSpeechSummary', 'renderSpeech', 'renderFrames']
for name, s, e in all_blocks:
    block_text = ''.join(lines[s-1:e-1])
    defs = find_real_defs(block_text)
    relevant = [(src_line, code) for src_line, code in defs if any(fn in code for fn in target)]
    if relevant:
        print(f"\n{name} (L{s}-L{e-1}):")
        for src_line, code in relevant:
            print(f"  src L{src_line}: {code[:60]}")
