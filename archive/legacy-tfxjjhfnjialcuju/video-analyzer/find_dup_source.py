import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Check which block contains the second occurrence of each function
blocks_to_check = {
    'processFile': [('CT_META', 1066, 1093), ('GET_PHASE_FN', 1002, 1065), ('ANALYZE_FN', 728, 848)],
    'renderSpeechSummary': [('RENDER_OVERVIEW', 1261, 1308), ('RENDER_REPORT_FN', 1521, 1612)],
    'renderFrames': [('RENDER_CHARTS', 1410, 1464), ('RENDER_REPORT_FN', 1521, 1612)],
}

for fn, blocks in blocks_to_check.items():
    print(f"\nChecking {fn}:")
    for block_name, start, end in blocks:
        block_text = ''.join(lines[start-1:end-1])
        count = block_text.count(f'function {fn}')
        if count > 0:
            print(f"  {block_name} (L{start}-L{end-1}): contains {count}x '{fn}'")
        else:
            # Check for processFile specifically
            count2 = block_text.count(f'async function {fn}')
            if count2 > 0:
                print(f"  {block_name} (L{start}-L{end-1}): contains {count2}x 'async function {fn}'")

# More thorough: check ALL blocks
print("\n--- ALL BLOCKS ---")
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
target_funcs = ['processFile', 'renderSpeechSummary', 'renderSpeech', 'renderFrames']
for name, s, e in all_blocks:
    block_text = ''.join(lines[s-1:e-1])
    found = []
    for fn in target_funcs:
        c1 = block_text.count(f'function {fn}')
        c2 = block_text.count(f'async function {fn}')
        if c1: found.append(f'function {fn}(x{c1})')
        if c2: found.append(f'async function {fn}(x{c2})')
    if found:
        print(f"  {name} ({s}-{e}): {', '.join(found)}")
