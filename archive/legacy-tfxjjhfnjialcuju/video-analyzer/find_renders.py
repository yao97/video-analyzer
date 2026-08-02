fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for kw in ["function renderStructure", "function renderReport", "function renderOverview", "function renderSpeechSummary", "function downloadReport", "function downloadFrames"]:
    for i, line in enumerate(lines):
        if kw in line:
            print("L" + str(i+1) + ":", line.rstrip())
            break
