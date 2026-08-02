fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# CT_META goes from 1066 to 1235
print("Last 5 lines of CT_META (1231-1235):")
for i in range(1230, 1236):
    if i < len(lines):
        print(f"  L{i+1}: {lines[i]!r}")

# And one more
print("L1236:", lines[1235].rstrip() if len(lines) > 1235 else "N/A")

# What does CT_META end with in the built file?
v3_path = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(v3_path, "r", encoding="utf-8") as f:
    v3 = f.read()

# Find CT_META end in v3 (processFile is in CT_META)
# Find the closing </div>` of the innerHTML in v3
div_close_v3 = v3.find("</div>`")
print(f"\n</div>` in v3 at char: {div_close_v3}")
print("Context after </div>`:")
print(repr(v3[div_close_v3:div_close_v3+100]))
