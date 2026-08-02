fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Show L1236-1260
for i in range(1235, 1260):
    if i < len(lines):
        print("L" + str(i+1) + ":", repr(lines[i].rstrip()[:100]))
