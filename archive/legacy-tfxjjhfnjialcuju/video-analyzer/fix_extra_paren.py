fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Current broken: font-size:0.75.rem;"/>`););
# Should be: font-size:0.75.rem;"/>`);
# The double )) is wrong - remove one )

old = 'font-size:0.75rem;"/>`););'
new = 'font-size:0.75rem;"/>`);'

idx = html.find(old)
print(f"Broken pattern at: {idx}")
if idx >= 0:
    new_html = html.replace(old, new)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"Old: {len(html)}, New: {len(new_html)}")
    print("FIXED")
else:
    print("Pattern not found")
