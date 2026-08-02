fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find renderReport start and end
for i in range(1519, 1620):
    if i < len(lines):
        print(f"L{i+1}: {repr(lines[i].rstrip()[:70])}")
