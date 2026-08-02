import re, sys

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Extract JS
m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if m:
    js = m.group(1)
    print(f"JS length: {len(js)} chars")
    outpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\temp_check.js"
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"Written to {outpath}")

    # Show lines 645-660
    lines = js.split('\n')
    print(f"\nLines 645-660:")
    for i in range(644, 660):
        if i < len(lines):
            print(f"  {i+1}: {lines[i]!r}")
else:
    print("No JS found")
