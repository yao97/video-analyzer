fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

print("Bytes 50525-50560:")
for i in range(50525, 50560):
    b = data[i]
    c = chr(b) if 32 <= b < 127 else f"\\x{b:02x}"
    print(f"  {i}: {b:3d} {c}")
