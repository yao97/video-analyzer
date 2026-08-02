fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Search for the exact pattern that was applied
# The original bad pattern: font-size:0.75.rem;"></code>`); 
# The wrong fix: font-size:0.75.rem;"&gt;&lt;/code&gt;`);  (but in JS &gt; is literal text)
# My latest fix: font-size:0.75.rem;"/>`);;  ← double ))

# Search for these patterns
p1 = 'font-size:0.75.rem;"/>`'
p2 = 'font-size:0.75.rem;"&gt;'
p3 = 'font-size:0.75.rem;"></code>`'

for pname, pat in [("self-close", p1), ("entity", p2), ("original", p3)]:
    idx = html.find(pat)
    print(f"{pname}: at {idx}")
    if idx >= 0:
        print(f"  Content: {repr(html[idx:idx+60])}")
