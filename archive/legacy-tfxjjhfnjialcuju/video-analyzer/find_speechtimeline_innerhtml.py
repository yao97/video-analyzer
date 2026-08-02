fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

bu = data.find(b"Backend unavailable")
print("BU at:", bu)

# Find the speechTimeline innerHTML specifically
st_ih = data.find(b"speechTimeline').innerHTML =", bu-500)
print("speechTimeline innerHTML at:", st_ih)

if st_ih >= 0:
    print("Context:", repr(data[st_ih:st_ih+50]))
    
    # Find the template literal opening backtick
    bt = data.find(b"`", st_ih)
    print("Template backtick at:", bt)
    print("Template content:", repr(data[bt:bt+200]))
