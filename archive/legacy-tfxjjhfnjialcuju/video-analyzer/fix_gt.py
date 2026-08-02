fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Find the problematic innerHTML template literal
bad = '<code style="background:#232636;padding:0.3rem 0.6rem;border-radius:6px;display:inline-block;margin-top:0.5rem;font-size:0.75rem;"></code>`);'
idx = html.find(bad)
print(f"Found at: {idx}")
if idx >= 0:
    print("Found!")
    # Replace with HTML entity for >
    fixed = '<code style="background:#232636;padding:0.3rem 0.6rem;border-radius:6px;display:inline-block;margin-top:0.5rem;font-size:0.75rem;"&gt;&lt;/code&gt;`);'
    new_html = html.replace(bad, fixed)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"Old: {len(html)}, New: {len(new_html)}")
    print("FIXED")
else:
    print("Pattern not found - checking partial")
    partial = 'font-size:0.75.rem;"></code>`'
    idx2 = html.find(partial)
    print(f"Partial at: {idx2}")
    if idx2 >= 0:
        print(html[idx2-100:idx2+100])
