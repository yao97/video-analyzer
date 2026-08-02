import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

def block(s, e):
    return ''.join(lines[s-1:e-1])

# Build v3_script from blocks (SAME as build_v3.py)
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
RENDER_SPEECH_S = block(1308, 1323)
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

# Find where renderSpeechSummary appears in each block
for name, content in [
    ('RENDER_OVERVIEW', RENDER_OVERVIEW),
    ('RENDER_SPEECH_S', RENDER_SPEECH_S),
    ('RENDER_SPEECH', RENDER_SPEECH),
]:
    matches = [(m.start(), m.group()) for m in re.finditer(r'function renderSpeechSummary', content)]
    print(f"{name}: {len(matches)} occurrences of 'function renderSpeechSummary'")
    if matches:
        for pos, grp in matches:
            ctx = content[max(0,pos-20):pos+60]
            print(f"  pos {pos}: {repr(ctx)}")

print()
# Now find where renderFrames appears
for name, content in [
    ('RENDER_CHARTS', RENDER_CHARTS),
    ('RENDER_STRUCT', RENDER_STRUCT),
    ('RENDER_REPORT_FN', RENDER_REPORT_FN),
    ('RENDER_FRAMES', RENDER_FRAMES),
]:
    matches = [(m.start(), m.group()) for m in re.finditer(r'function renderFrames', content)]
    print(f"{name}: {len(matches)} occurrences of 'function renderFrames'")
    if matches:
        for pos, grp in matches:
            ctx = content[max(0,pos-20):pos+60]
            print(f"  pos {pos}: {repr(ctx)}")

print()
# Check GET_PHASE_FN for processFile
matches = [(m.start(), m.group()) for m in re.finditer(r'async function processFile', GET_PHASE_FN)]
print(f"GET_PHASE_FN: {len(matches)} occurrences of 'async function processFile'")
