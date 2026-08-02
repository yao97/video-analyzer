fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, encoding="utf-8") as f:
    html = f.read()

# Find the broken section by searching for the specific pattern
idx = html.find("innerHTML = `<div style=\"color:var(--yellow)\"")
print(f"Found at: {idx}")
if idx >= 0:
    snippet = html[idx:idx+500]
    print("Content:")
    print(repr(snippet))
    print()
    # Find where it should close - look for the pattern that should be after
    # The template literal should close with </code>`);
    # In the broken version, it closes prematurely at the next backtick
    
    # Show what immediately follows the <code> tag
    after_code = html.find("</code>", idx)
    print(f"</code> at: {after_code}")
    if after_code >= 0:
        print("After </code>:")
        print(repr(html[after_code:after_code+200]))
