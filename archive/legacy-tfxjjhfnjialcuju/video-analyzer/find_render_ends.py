fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Show lines 1370-1382
for i in range(1369, 1382):
    if i < len(lines):
        print(f"L{i+1}: {repr(lines[i].rstrip()[:70])}")

print()
# Show lines 1320-1330
for i in range(1319, 1330):
    if i < len(lines):
        print(f"L{i+1}: {repr(lines[i].rstrip()[:70])}")

print()
# Find renderSpeech end
for i in range(1319, 1400):
    if i < len(lines) and lines[i].strip() == '}' and i > 1324:
        print(f"Potential renderSpeech end at L{i+1}: {lines[i].rstrip()[:70]}")
        # Show context
        for j in range(max(1319, i-2), min(len(lines), i+3)):
            print(f"  L{j+1}: {repr(lines[j].rstrip()[:70])}")
        break
