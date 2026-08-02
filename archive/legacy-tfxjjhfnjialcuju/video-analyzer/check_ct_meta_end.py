fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# CT_META = block(1066, 1236) = lines[1065:1235] = L1066 to L1235
# Let me see what's at the end of CT_META (L1220-1236)
for i in range(1219, 1236):
    if i < len(lines):
        print("L" + str(i+1) + ":", repr(lines[i].rstrip()[:100]))
