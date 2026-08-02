fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# Search for the broken section - find the pattern in raw bytes
# Looking for: speechTimeline').innerHTML = `
raw_search = b"speechTimeline').innerHTML = `"
positions = []
pos = 0
while True:
    pos = data.find(raw_search, pos)
    if pos < 0:
        break
    positions.append(pos)
    pos += 1

print(f"Found {len(positions)} occurrences of broken pattern")
for i, p in enumerate(positions[:3]):
    print(f"\nOccurrence {i+1} at byte {p}:")
    chunk = data[p:p+300]
    # Show hex of first 100 bytes after position
    print("First 100 bytes (hex):", chunk[:100].hex())
    print("As text:", chunk[:200])
