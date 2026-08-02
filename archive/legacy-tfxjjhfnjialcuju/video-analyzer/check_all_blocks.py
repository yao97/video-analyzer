fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Verify all blocks - show first and last line of each block
blocks = {
    'COLOR_RGB': (498, 545),
    'CONTENT_RULES': (546, 679),
    'SCORE_FN': (680, 716),
    'DETECT_FN': (717, 727),
    'ANALYZE_FN': (728, 848),
    'SCENE_FN': (849, 860),
    'BUILD_PHASES_FN': (861, 881),
    'TRANSCRIBE_JS': (897, 916),
    'POLL_JS': (901, 982),
    'GEN_SCRIPT_FN': (983, 1001),
    'GET_PHASE_FN': (1002, 1065),
    'CT_META': (1066, 1093),
    'PROCESS_FN': (1093, 1246),
    'RENDER_METRICS': (1233, 1243),
    'RENDER_OVERVIEW': (1244, 1290),
    'RENDER_SPEECH_S': (1308, 1323),
    'RENDER_SPEECH': (1324, 1375),
    'RENDER_STRUCT_AND_REPORT': (1361, 1379),  # guess
    'RENDER_FRAMES': (1380, 1404),
    'DESTROY_CHARTS': (1405, 1409),
    'RENDER_CHARTS': (1410, 1464),
    'RENDER_REPORT': (1465, 1612),
    'DOWNLOAD_REPORT': (1613, 1622),
    'DOWNLOAD_FRAMES': (1623, 1634),
    'INIT_CODE': (1635, 1640),
}

for name, (start, end) in sorted(blocks.items(), key=lambda x: x[1][0]):
    if start <= len(lines):
        first = lines[start-1].rstrip()[:60] if start > 0 else ""
        last = lines[end-1].rstrip()[:60] if end > 0 else ""
        print(f"{name:30s} L{start:4d}-L{end:4d}: {repr(first)}")
        print(f"{'':30s}               end: {repr(last)}")
