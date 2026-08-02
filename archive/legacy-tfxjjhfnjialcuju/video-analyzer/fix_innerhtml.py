import sys
fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, encoding="utf-8") as f:
    html = f.read()

# Find the broken section
idx = html.index("innerHTML = `")
snippet = html[idx:idx+400]
print(f"Found at {idx}:")
print(repr(snippet[:300]))
