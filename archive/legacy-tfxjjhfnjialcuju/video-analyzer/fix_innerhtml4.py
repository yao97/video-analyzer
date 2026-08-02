import sys
fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, encoding="utf-8") as f:
    html = f.read()

# The broken section starts at 46086
broken_start = 46086
# Show 500 chars from broken start
snippet = html[broken_start:broken_start+500]
print("Chars from 46086:")
for i, ch in enumerate(snippet):
    if i > 0 and i % 100 == 0:
        print()
    print(repr(ch)[1:-1], end='')  # strip quotes
print()
print()
print(f"Total shown: {len(snippet)} chars")
