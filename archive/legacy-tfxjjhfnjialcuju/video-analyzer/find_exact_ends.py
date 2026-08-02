fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find exact ends of render functions
funcs = [
    ('renderSpeechSummary', 1308),
    ('renderSpeech', 1324),
    ('renderFrames', 1380),
    ('destroyCharts', 1405),
    ('renderCharts', 1410),
    ('renderStructure', 1465),
    ('downloadReport', 1613),
    ('downloadFrames', 1623),
]

for name, start_line in funcs:
    depth = 0
    for i in range(start_line-1, min(start_line+300, len(lines))):
        for ch in lines[i]:
            if ch == '{': depth += 1
            elif ch == '}': 
                depth -= 1
                if depth == 0:
                    print(f"{name}: L{start_line}-L{i+1} ({(i+1)-start_line+1} lines)")
                    break
        if depth == 0:
            break
