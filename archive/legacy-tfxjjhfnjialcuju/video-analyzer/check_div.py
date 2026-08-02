path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Find <div class="container">
idx = content.find('<div class="container">')
print(f'Container div at pos: {idx}')
print(f'Context: {repr(content[idx-30:idx+100])}')
print()

# Count div tags in HTML (not CSS)
# Find position of first <script> tag - before that is HTML
script_idx = content.find('<script src=')
print(f'First script at: {script_idx}')
print(f'HTML part: {content[script_idx-200:script_idx+50]!r}')
