fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Find the innerHTML with the broken template literal
idx = html.find("speechTimeline').innerHTML = `<div style=\"color:var(--yellow)\"")
print(f"innerHTML at: {idx}")

if idx >= 0:
    snippet = html[idx:idx+500]
    print("Snippet:")
    print(repr(snippet))
