fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Current: <code style="...font-size:0.75.rem;"${"/"}>` 
# The code tag is empty - just remove it entirely
# We need to find the pattern that starts with <code style=... and ends with ${"/"}>` 
# and replace it with nothing

# Search for the code tag
old = '<code style="background:#232636;padding:0.3rem 0.6rem;border-radius:6px;display:inline-block;margin-top:0.5rem;font-size:0.75rem;"${"/"}>`'
idx = html.find(old)
print(f"Code tag at: {idx}")

if idx >= 0:
    new_html = html.replace(old, '')
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"Old: {len(html)}, New: {len(new_html)}")
    print("FIXED - removed empty code tag")
else:
    print("Pattern not found - checking partial")
    partial = '<code style="background:#232636'
    idx2 = html.find(partial)
    print(f"Partial at: {idx2}")
    if idx2 >= 0:
        print(repr(html[idx2:idx2+200]))
