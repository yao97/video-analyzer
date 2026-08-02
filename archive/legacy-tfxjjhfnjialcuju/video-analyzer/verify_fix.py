fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

html = data.decode("utf-8")

# Verify: check the fixed section
idx = html.find("speechTimeline').innerHTML = `<div style=\"color:var(--yellow)\"")
if idx < 0:
    print("ERROR: fixed section not found!")
else:
    snippet = html[idx:idx+300]
    print("Fixed section:")
    print(snippet)
    print()

# Check that buildPhases is now a proper function (not inside template literal)
bp_idx = html.find("function buildPhases")
print(f"buildPhases at: {bp_idx}")
bp_snippet = html[bp_idx:bp_idx+100]
print(bp_snippet)
print()

# Check that the else block closes properly
else_idx = html.find("setBadge('badgeSpeech','fail','服务未启动')")
# Find the section after this
sec = html[else_idx:else_idx+300]
print("After setBadge:")
print(sec)
