fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Show lines 1460-1480
for i in range(1459, 1480):
    if i < len(lines):
        print(f"L{i+1}: {repr(lines[i].rstrip()[:70])}")
