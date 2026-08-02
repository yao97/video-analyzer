fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Current: font-size:0.75.rem;"/>`);
# The /> is parsed as division / then >
# Fix: use ${'/'} to break the /  pattern
# Change: "font-size:0.75.rem;"/>`);  → "font-size:0.75.rem;"${'/'}>`);

old = 'font-size:0.75rem;"/>`'
new = 'font-size:0.75rem;"${"/"}>`'

idx = html.find(old)
print(f"Found at: {idx}")

if idx >= 0:
    # Show context
    print(f"Context: {repr(html[idx-50:idx+80])}")
    new_html = html.replace(old, new)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"Old: {len(html)}, New: {len(new_html)}")
    print("FIXED")
else:
    print("Not found!")
