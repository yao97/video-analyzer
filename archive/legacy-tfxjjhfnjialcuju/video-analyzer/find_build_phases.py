fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find buildPhases in source
for i, line in enumerate(lines):
    if 'buildPhases' in line or 'phaseLogic' in line:
        print("L" + str(i+1) + ":", line.rstrip()[:80])
