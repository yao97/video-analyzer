fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "rb") as f:
    data = f.read()

bu = data.find(b"Backend unavailable")
print("BU at:", bu)

# Find innerHTML template literal in source
eq_bt = data.find(b"= `", bu)
print("= ` at:", eq_bt)

# Look for the <br> in this section
chunk = data[eq_bt:eq_bt+500]
br_pos = chunk.find(b'<br>')
print("<br> at relative:", br_pos)
if br_pos >= 0:
    print("Context:", repr(chunk[br_pos-10:br_pos+40]))
