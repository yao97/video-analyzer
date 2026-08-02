fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

bu = data.find(b"Backend unavailable")
eq_bt = data.find(b"= `", bu)
print("Template opening at:", eq_bt)

# Show the template from start to 50 chars after the <br>
# Find <br> in this template
br_pos = data.find(b'<br>', eq_bt)
print("<br> at:", br_pos)

# Show 100 chars around <br>
print("Around <br>:")
for i in range(br_pos-5, br_pos+30):
    b = data[i]
    c = chr(b) if 32 <= b < 127 else f"\\x{b:02x}"
    print(f"  {i}: {b:3d} {c}")
