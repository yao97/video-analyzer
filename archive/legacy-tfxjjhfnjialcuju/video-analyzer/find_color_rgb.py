fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Show lines 500-545 to find where COLOR_RGB actually starts
for i in range(499, 545):
    if i < len(lines):
        print(f"L{i+1}: {lines[i].rstrip()}")
