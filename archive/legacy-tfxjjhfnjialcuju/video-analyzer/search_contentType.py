import re

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Find all occurrences of 'contentType'
occurrences = []
start = 0
while True:
    idx = content.find('contentType', start)
    if idx == -1:
        break
    # Get context
    ctx_start = max(0, idx - 100)
    ctx_end = min(len(content), idx + 200)
    ctx = content[ctx_start:ctx_end]
    occurrences.append((idx, ctx))
    start = idx + 1

print(f'Found {len(occurrences)} occurrences of contentType\n')

# Show first 10 occurrences
for i, (idx, ctx) in enumerate(occurrences[:10]):
    print(f'--- Occurrence {i+1} at position {idx} ---')
    print(ctx)
    print()
