fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

bu = data.find(b"Backend unavailable")
print("BU at:", bu)

# Find the line with innerHTML = ` in the BU section
# Search backwards from BU for "innerHTML ="
ih = data.rfind(b"innerHTML =", 0, bu+50)
print("innerHTML = found at:", ih)

if ih >= 0:
    print("Context:", repr(data[ih:ih+100]))
