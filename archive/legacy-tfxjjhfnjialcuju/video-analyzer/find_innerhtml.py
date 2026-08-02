fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, encoding="utf-8") as f:
    html = f.read()

# Search for innerHTML with the div style
idx = html.find("innerHTML = ")
print(f"innerHTML = at: {idx}")

# Find all occurrences
occurrences = []
pos = 0
while True:
    pos = html.find("innerHTML = `", pos)
    if pos < 0:
        break
    occurrences.append(pos)
    pos += 1

print(f"Total occurrences of 'innerHTML = `': {len(occurrences)}")
for i, occ in enumerate(occurrences):
    snippet = html[occ:occ+200]
    print(f"\nOccurrence {i+1} at {occ}:")
    print(repr(snippet[:200]))
