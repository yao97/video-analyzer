fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# CT_META = block(1066, 1236) = lines[1065:1235] = L1066-L1235
print("L1234:", repr(lines[1233][:60]))
print("L1235:", repr(lines[1234][:60]))
print("L1236:", repr(lines[1235][:60]))
print("L1237:", repr(lines[1236][:60]))
print("L1238:", repr(lines[1237][:60]))
