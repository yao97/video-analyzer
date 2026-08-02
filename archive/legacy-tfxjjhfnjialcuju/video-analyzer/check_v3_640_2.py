import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if m:
    js = m.group(1)
    lines = js.split('\n')
    for i in range(609, 710):
        if i < len(lines):
            print("L" + str(i+1) + ":", repr(lines[i].rstrip()[:80]))
