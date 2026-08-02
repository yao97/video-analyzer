fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find("Backend unavailable")
print(f"'Backend unavailable' at: {idx}")

if idx >= 0:
    snippet = html[idx:idx+300]
    print("Snippet:")
    print(repr(snippet))
    print()
    
    # Find the next backtick after this section
    # (the closing of the template literal)
    next_bt = html.find("`", idx + 50)
    print(f"Next backtick at: {next_bt}")
    print(f"Context: {repr(html[next_bt-30:next_bt+30])}")
