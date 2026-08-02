fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

import re
m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if m:
    js = m.group(1)
    lines = js.split('\n')
    for i, line in enumerate(lines):
        if 'const show' in line or 'const hide' in line or 'const toast' in line or 'const switchTab' in line:
            print(f"L{i+1}: {line.rstrip()}")
