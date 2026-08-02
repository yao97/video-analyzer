import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
outpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\v3_lines.txt"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if m:
    js = m.group(1)
    lines = js.split('\n')
    with open(outpath, "w", encoding="utf-8") as f:
        for i in range(609, 720):
            if i < len(lines):
                f.write(f"L{i+1}: {lines[i]}\n")
print(f"Total JS lines: {len(lines)}")
