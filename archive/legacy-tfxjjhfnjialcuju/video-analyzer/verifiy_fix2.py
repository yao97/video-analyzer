path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Count script tags
import re
starts = len(re.findall(r'<script[^>]*>', content))
ends = content.count('</script>')
print(f'<script> starts: {starts}')
print(f'</script> ends: {ends}')

# Check chart.js line
idx = content.find('chart.js@4.4.0')
if idx > 0:
    print('\nChart.js context:')
    print(content[idx-20:idx+150])
