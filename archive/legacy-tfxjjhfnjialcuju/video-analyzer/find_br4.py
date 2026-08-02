fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

bu = data.find(b"Backend unavailable")
# Find the start of the template literal: after = ` 
eq_bt = data.find(b"= `", bu)
print("= ` at:", eq_bt)
if eq_bt >= 0:
    # Show bytes from = ` to 200 bytes after
    chunk = data[eq_bt:eq_bt+200]
    print("Template literal start:")
    for i, b in enumerate(chunk[:100]):
        c = chr(b) if 32 <= b < 127 else f"\\x{b:02x}"
        print(f"{i:3d} {b:3d} {c}", end="  ")
        if (i+1) % 5 == 0:
            print()
    print()
    
    # Find the last 100 bytes before the closing
    print("Last 50 bytes of this section:")
    for i, b in enumerate(chunk[-50:]):
        idx = eq_bt + 200 - 50 + i
        c = chr(b) if 32 <= b < 127 else f"\\x{b:02x}"
        print(f"{idx} {b:3d} {c}", end="  ")
        if (i+1) % 5 == 0:
            print()
