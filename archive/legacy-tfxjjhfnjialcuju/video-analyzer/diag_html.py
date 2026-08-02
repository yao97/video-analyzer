import re

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if not m:
    print("No script found")
    exit()
js = m.group(1)
print(f"JS length from HTML: {len(js)}")

# Check each function - look for DEFINITIONS (at start of line or after comment)
for fn_name in ['processFile', 'renderSpeechSummary', 'renderSpeech', 'renderFrames']:
    pattern = r'function ' + fn_name
    matches = list(re.finditer(pattern, js))
    if len(matches) > 1:
        print(f"\n{fn_name}: {len(matches)} occurrences")
        for i, m2 in enumerate(matches):
            # Show context before
            start = max(0, m2.start()-50)
            before = js[start:m2.start()]
            lines_before = before.count('\n') + 1
            print(f"  [{i}] pos {m2.start()}, line {lines_before} before: {repr(before[-40:])}")
            print(f"  [{i}] after: {repr(js[m2.start():m2.start()+60])}")
    elif len(matches) == 1:
        print(f"{fn_name}: unique")
    else:
        print(f"{fn_name}: not found")
