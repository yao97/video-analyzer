fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

bu = data.find(b"Backend unavailable")
print("BU at:", bu)

# Find speechTimeline innerHTML in v3
st = data.find(b"speechTimeline', bu)
print("speechTimeline at:", st)

# Find all = ` in the area
for i in range(bu-200, bu+50):
    if data[i] == 96 and (i == 0 or data[i-1] <= 32):
        print(f"Backtick at {i} (possibly opening): {repr(data[i-3:i+20])}")
