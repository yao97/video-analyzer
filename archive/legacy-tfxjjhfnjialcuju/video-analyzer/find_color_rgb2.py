fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Show lines 494-505
for i in range(493, 506):
    if i < len(lines):
        print("L" + str(i+1) + ":", repr(lines[i].rstrip()[:80]))
