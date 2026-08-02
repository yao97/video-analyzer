import re

# Read the GENERATED v3_script from the HTML
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if not m:
    print("No script found")
    exit()
v3_script = m.group(1)
print(f"v3_script length: {len(v3_script)}")

# Find ALL occurrences of each function - with context
for fn_name in ['processFile', 'renderSpeechSummary', 'renderSpeech', 'renderFrames']:
    pattern = r'function ' + fn_name
    matches = [(m.start(), m.end(), v3_script[max(0,m.start()-30):m.end()+50]) 
               for m in re.finditer(pattern, v3_script)]
    if len(matches) > 1:
        print(f"\n{fn_name}: {len(matches)} occurrences:")
        for start, end, ctx in matches:
            print(f"  pos {start}-{end}: ...{repr(ctx)}...")
    elif len(matches) == 1:
        print(f"\n{fn_name}: UNIQUE at {matches[0][0]}")
    else:
        print(f"\n{fn_name}: NOT FOUND")
