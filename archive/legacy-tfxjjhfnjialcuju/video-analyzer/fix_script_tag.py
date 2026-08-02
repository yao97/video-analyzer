path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# The issue: <script src="chart.js"> is missing </script> before the inline <script>
# Find the pattern and fix it
old = '>\n<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js">\n    <script>'
new = '>\n<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>\n    <script>'

if old in content:
    content = content.replace(old, new, 1)
    print('Fixed: Added </script> for chart.js')
else:
    print('Pattern not found, checking...')
    idx = content.find('chart.js@4.4.0')
    if idx > 0:
        print('Context:', repr(content[idx-50:idx+150]))

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
