path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Check if button exists
if '上传新视频' in content:
    print('✓ Button "上传新视频" found')
    idx = content.find('上传新视频')
    print('Context:', repr(content[idx-100:idx+200]))
else:
    print('✗ Button not found')

# Also check if leftPanel structure is correct
print('\nleftPanel closing check:')
idx2 = content.find('</div>\n<div id="rightPanel">')
if idx2 > 0:
    print('Found rightPanel, context:', repr(content[idx2-200:idx2+50]))
