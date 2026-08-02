fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

bu = data.find(b"Backend unavailable")
print("BU at:", bu)
# Show first 500 chars after BU
chunk = data[bu:bu+500]
print("Chunk:")
print(chunk.decode('utf-8', errors='replace'))
