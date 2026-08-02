with open(r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\temp_check.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Total lines:", len(lines))
# Show lines 640-665
for i in range(639, 665):
    if i < len(lines):
        print(f"{i+1}: {lines[i]!r}")
