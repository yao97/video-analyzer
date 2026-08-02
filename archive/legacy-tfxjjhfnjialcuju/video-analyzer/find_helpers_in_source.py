fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Check CT_META = block(1066, 1236) = lines[1065:1235]
print("L1066:", lines[1065].rstrip())
print("L1067:", lines[1066].rstrip())

# Find where helpers are in source
for i, line in enumerate(lines):
    if 'const show = id =>' in line:
        print(f"const show at L{i+1}: {line.rstrip()}")

# Check if helpers appear in CT_META range
ct_content = "".join(lines[1065:1235])
print("\nHas 'const show' in CT_META?", 'const show' in ct_content)
print("First 200 chars of CT_META:", ct_content[:200])
