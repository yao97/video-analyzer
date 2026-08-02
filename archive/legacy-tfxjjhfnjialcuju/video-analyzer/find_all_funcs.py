fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find key function boundaries
targets = [
    'function renderOverview',
    'function renderSpeechSummary',
    'function renderSpeech',
    'function renderOverviewFinal',
    'function renderStructureFinal',
    'function renderReportFinal',
    'function renderFrames',
    'function destroyCharts',
    'function renderCharts',
    'function renderStructure',
    'function renderReport',
    'function downloadReport',
    'async function downloadFrames',
]

for target in targets:
    for i, line in enumerate(lines):
        if target in line:
            print(f"{target} at L{i+1}: {line.rstrip()[:70]}")
            break

# Also find blank/comment before renderOverview
print()
for i in range(1242, 1265):
    if i < len(lines):
        print(f"L{i+1}: {repr(lines[i].rstrip()[:70])}")
