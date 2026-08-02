fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# CT_META = block(1066, 1246) = lines[1065:1245] = L1066-L1245
ct = "".join(lines[1065:1245])
print("CT_META (L1066-L1245) length:", len(ct))
print("First 80 chars:", repr(ct[:80]))
print("Last 80 chars:", repr(ct[-80:]))

# What's at L1066?
print("\nL1066:", repr(lines[1065][:80]))

# Where does processFile actually start in source?
for i, line in enumerate(lines):
    if 'async function processFile' in line:
        print(f"\nprocessFile in source at L{i+1}: {line.rstrip()[:60]}")
        break

# Where does processFile end in source?
for i in range(len(lines)-1, -1, -1):
    if 'async function processFile' in lines[i]:
        # Find the closing }
        # Look for the pattern after a long function
        print(f"processFile starts at L{i+1}")
        # Count braces
        depth = 0
        for j in range(i, min(i+300, len(lines))):
            for ch in lines[j]:
                if ch == '{': depth += 1
                elif ch == '}': depth -= 1
                if depth == 0 and j > i:
                    print(f"processFile ends at L{j+1}: {lines[j].rstrip()[:60]}")
                    break
        break
