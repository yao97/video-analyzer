fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Find the else block in processFile
else_idx = html.find("setBadge('badgeSpeech','fail','服务未启动')")
# Show context after this - the else block content
sec = html[else_idx:else_idx+500]
print("else block:")
print(sec)
print()

# Check if there's now a proper closing of the else block
# Look for the pattern after </code>`); followed by }
idx2 = html.find("</code>`);", else_idx)
if idx2 >= 0:
    print(f"</code>`); found at {idx2}")
    print(html[idx2:idx2+50])
else:
    print("</code>`); NOT FOUND!")
