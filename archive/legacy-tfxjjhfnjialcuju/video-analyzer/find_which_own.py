import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

def block(s, e):
    return ''.join(lines[s-1:e-1])

blocks = {
    'GET_PHASE_FN': block(1002, 1065),
    'CT_META': block(1066, 1093),
    'PROCESS_FN': block(1093, 1246),
    'RENDER_OVERVIEW': block(1261, 1308),
    'RENDER_SPEECH_S': block(1308, 1323),
    'RENDER_SPEECH': block(1324, 1375),
    'RENDER_FINAL': block(1376, 1380),
    'RENDER_FRAMES': block(1380, 1404),
    'RENDER_CHARTS': block(1410, 1464),
    'RENDER_STRUCT': block(1465, 1520),
    'RENDER_REPORT_FN': block(1521, 1612),
}

# For each block, show the FIRST and LAST 3 lines + check for target functions
target = ['processFile', 'renderSpeechSummary', 'renderSpeech', 'renderFrames']
for name, content in blocks.items():
    content_lines = content.split('\n')
    fn_found = []
    for fn in target:
        pattern = 'function ' + fn if fn != 'processFile' else 'async function processFile'
        for i, line in enumerate(content_lines):
            stripped = line.lstrip()
            if stripped.startswith(pattern) or (fn == 'processFile' and 'async function processFile' in line and i == 0):
                fn_found.append(f"{fn} at line {i+1}")
    if fn_found:
        print(f"\n{name}:")
        print(f"  FIRST 3: {repr(content_lines[:3])}")
        print(f"  LAST 3:  {repr(content_lines[-3:])}")
        print(f"  FOUND: {fn_found}")
    else:
        # Still show boundaries
        if name in ['CT_META', 'PROCESS_FN', 'RENDER_SPEECH_S', 'RENDER_SPEECH', 'RENDER_FRAMES']:
            print(f"\n{name} (no target fn):")
            print(f"  FIRST 3: {repr(content_lines[:3])}")
            print(f"  LAST 3:  {repr(content_lines[-3:])}")
