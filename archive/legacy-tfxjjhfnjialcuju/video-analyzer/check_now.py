fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# Find the area around the innerHTML template literal
pos = data.find(b"Backend unavailable")
print("Backend unavailable at:", pos)

# Find the <br> in that section
br_pos = data.find(b'<br>', pos)
print("<br> at:", br_pos)
print("Context:", repr(data[br_pos-5:br_pos+20]))

# Find the next ` after the <br>
next_bt = data.find(b'`', br_pos)
print("Next backtick after <br> at:", next_bt)
print("Context:", repr(data[next_bt-10:next_bt+20]))
