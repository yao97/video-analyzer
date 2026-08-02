fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# CT_META = block(1066, 1246) = lines[1065:1245] = L1066-L1245
# Show the last 20 lines of CT_META
ct_lines = lines[1065:1245]
print("Last 20 lines of CT_META:")
for i, line in enumerate(ct_lines[-20:]):
    actual_line = 1065 + len(ct_lines) - 20 + i
    print(f"  L{actual_line+1}: {line.rstrip()[:80]}")

# Also show what v3_script includes in order
print()
print("Blocks in v3_script order:")
blocks = [
    ("COLOR_RGB", 498, 545),
    ("CONTENT_RULES", 546, 679),
    ("SCORE_FN", 680, 716),
    ("DETECT_FN", 717, 727),
    ("ANALYZE_FN", 728, 848),
    ("SCENE_FN", 849, 860),
    ("BUILD_PHASES_FN", 861, 881),
    ("TRANSCRIBE_JS", 882, 900),
    ("POLL_JS", 901, 982),
    ("GEN_SCRIPT_FN", 983, 1001),
    ("GET_PHASE_FN", 1002, 1065),
    ("CT_META", 1066, 1246),
]
