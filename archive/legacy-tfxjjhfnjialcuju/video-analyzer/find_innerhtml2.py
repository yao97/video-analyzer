fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Search for the unique marker: Backend unavailable
idx = html.find("Backend unavailable")
print(f"Backend unavailable at: {idx}")

if idx >= 0:
    # Show the next 500 chars
    snippet = html[idx:idx+500]
    print("Snippet from 'Backend unavailable':")
    print(repr(snippet))
