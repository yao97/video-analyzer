fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Show L1243-1265
for i in range(1242, 1265):
    if i < len(lines):
        print("L" + str(i+1) + ":", repr(lines[i].rstrip()[:80]))
