fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Find the current broken content
idx = html.find('font-size:0.75rem;"/>`')
if idx < 0:
    idx = html.find('font-size:0.75rem;')
    print(f"font-size:0.75rem; at: {idx}")

# Show context around font-size:0.75.rem
idx = html.find("font-size:0.75rem;")
if idx >= 0:
    snippet = html[idx:idx+80]
    print(f"Context: {repr(snippet)}")
    
    # Current: font-size:0.75.rem;"/>`);  ← has extra )
    # Should be: font-size:0.75.rem;"/>`);   ← one )
    # OR: font-size:0.75.rem;"></code>`);  ← original, fixed
    # OR: font-size:0.75.rem;"+">"+</code>`);  ← HTML entity approach
    
    # Let me check what's there now
    current = html[idx:idx+50]
    print(f"Current: {repr(current)}")
