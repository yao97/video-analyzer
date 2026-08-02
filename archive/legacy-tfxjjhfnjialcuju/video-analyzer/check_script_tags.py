path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Find all script tags
import re
script_starts = [m.start() for m in re.finditer(r'<script', content)]
script_ends = [m.start() for m in re.finditer(r'</script>', content)]

print(f'<script> starts: {len(script_starts)}')
for pos in script_starts:
    print(f'  {pos}: {repr(content[pos:pos+80])}')

print(f'\n</script> ends: {len(script_ends)}')
for pos in script_ends:
    print(f'  {pos}: {repr(content[pos:pos+20])}')
