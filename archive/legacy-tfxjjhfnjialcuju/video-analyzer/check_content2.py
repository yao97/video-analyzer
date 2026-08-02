fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

def block(s, e):
    return ''.join(lines[s-1:e-1])

b = block(1308, 1323)
print(f"block(1308, 1323) = {len(b)} chars")
# Find function definitions at column 0
for i, l in enumerate(b.split('\n')):
    stripped = l.lstrip()
    if stripped.startswith('function ') or stripped.startswith('async '):
        print(f"  Line {i+1}: {repr(stripped[:60])}")

print()
b2 = block(1324, 1375)
print(f"block(1324, 1375) = {len(b2)} chars")
for i, l in enumerate(b2.split('\n')[:3]):
    stripped = l.lstrip()
    if stripped.startswith('function ') or stripped.startswith('async '):
        print(f"  Line {i+1}: {repr(stripped[:60])}")

# Now check: where does renderSpeechSummary() end in the source?
for i in range(1307, 1325):
    if i < len(lines):
        stripped = lines[i].rstrip()
        if stripped == '}':
            print(f"\nBlank/brace check at L{i+1}: {repr(stripped[:40])}")
