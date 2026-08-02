fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Show lines 895-910
for i in range(894, 912):
    if i < len(lines):
        print("L" + str(i+1) + ":", repr(lines[i].rstrip()[:80]))

# Also show lines 896-983 to find pollTranscribeResult boundaries
print()
for i in range(895, 983):
    if i < len(lines):
        print("L" + str(i+1) + ":", repr(lines[i].rstrip()[:80]))
