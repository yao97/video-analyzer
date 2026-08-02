import re

# Read the generated v3_script (extract from HTML)
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if not m:
    print("No script found")
    exit()
js = m.group(1)
print(f"v3_script length: {len(js)}")

# Find all instances of processFile
for fn in ['processFile', 'renderSpeechSummary', 'renderFrames']:
    positions = [m.start() for m in re.finditer(r'function ' + fn, js)]
    if len(positions) > 1:
        print(f"\n{fn} appears {len(positions)} times at positions: {positions}")
        for p in positions:
            # Show context around each occurrence
            start = max(0, p-20)
            end = min(len(js), p+100)
            print(f"  Pos {p}: ...{repr(js[start:end])}...")
    else:
        print(f"\n{fn}: unique at {positions[0] if positions else 'NOT FOUND'}")
