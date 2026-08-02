fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# Find the exact area around the <br> in the Backend unavailable section
bu = data.find(b"Backend unavailable")
eq_bt = data.find(b"= `", bu)
print("= ` at:", eq_bt)

# Look at the last 30 bytes of the template literal
end_area = eq_bt + 200 - 30
print("Area around template end:")
for i in range(eq_bt + 170, eq_bt + 210):
    b = data[i]
    c = chr(b) if 32 <= b < 127 else f"\\x{b:02x}"
    print(f"  {i}: {b:3d} {c}")

# Find all consecutive backticks
for i in range(len(data)-1):
    if data[i] == 96 and data[i+1] == 96:
        print(f"Double backtick at {i}")
