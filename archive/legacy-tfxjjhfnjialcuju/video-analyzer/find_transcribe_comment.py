fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find "// Transcribe API" or similar in source
for i, line in enumerate(lines):
    if 'transcribe' in line.lower() or 'Transcribe' in line or 'whisper' in line.lower():
        print(f"L{i+1}: {line.rstrip()[:80]}")
