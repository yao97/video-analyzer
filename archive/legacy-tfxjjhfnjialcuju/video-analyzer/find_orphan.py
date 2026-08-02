fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Search for "const phaseLogic = contentType.phaseLogic" in source
for i, line in enumerate(lines):
    if 'const phaseLogic = contentType.phaseLogic' in line:
        print(f"Found at L{i+1}: {line.rstrip()[:80]}")
        # Show context
        for j in range(max(0,i-2), min(len(lines), i+15)):
            print(f"  L{j+1}: {lines[j].rstrip()[:80]}")
        print()
