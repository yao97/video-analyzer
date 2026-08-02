fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

def block(s, e):
    return ''.join(lines[s-1:e-1])

# Show what block(1308, 1323) and block(1308, 1324) contain
b1 = block(1308, 1323)
b2 = block(1308, 1324)
print(f"block(1308, 1323): {len(b1)} chars, {len(b1.split(chr(10)))} lines")
print(f"block(1308, 1324): {len(b2)} chars, {len(b2.split(chr(10)))} lines")
print()
print("block(1308, 1323) last 5 lines:")
for i, l in enumerate(b1.split('\n')[-5:]):
    print(f"  {repr(l[:70])}")
print()
print("block(1308, 1324) last 5 lines:")
for i, l in enumerate(b2.split('\n')[-5:]):
    print(f"  {repr(l[:70])}")
