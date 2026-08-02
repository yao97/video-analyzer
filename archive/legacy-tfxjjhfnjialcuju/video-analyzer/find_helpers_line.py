fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Show lines 480-490
for i in range(479, 490):
    if i < len(lines):
        print(f"L{i+1}: {lines[i].rstrip()}")
