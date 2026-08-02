fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

import re
m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if m:
    js = m.group(1)
    lines = js.split('\n')
    # Find where CT_META starts
    # CT_META = block(1066, 1236) → should start with CT_META content
    # First content after Helpers should be COLOR_RGB block
    # Find the first line of CT_META in v3
    for i in range(0, 50):
        print(f"L{i+1}: {lines[i].rstrip()}")
