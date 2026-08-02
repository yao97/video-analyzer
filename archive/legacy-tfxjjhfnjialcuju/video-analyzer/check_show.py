fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\temp_check.js"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
# Show lines 1-50
for i, line in enumerate(lines[:60], 1):
    print(f"{i:3}: {line}", end='')
