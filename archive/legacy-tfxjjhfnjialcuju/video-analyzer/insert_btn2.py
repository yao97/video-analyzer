path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Actual text from debug output (no indentation)
old_block = (
    '<div id="speechPreviewText" style="font-size:0.78rem;color:#6b7084;">等待分析...</div>\n'
    '</div>\n'
    '</div>\n'
    '<div id="rightPanel">'
)

new_block = (
    '<div id="speechPreviewText" style="font-size:0.78rem;color:#6b7084;">等待分析...</div>\n'
    '</div>\n'
    '<button class="btn btn-secondary" style="margin-top:1rem;width:100%;" onclick="document.getElementById(\'fileInput\').click()">📤 上传新视频</button>\n'
    '</div>\n'
    '<div id="rightPanel">'
)

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    print('Button inserted successfully')
else:
    print('ERROR: old_block not found')
    # Show what's actually there
    idx = content.find('speechPreviewText')
    if idx > 0:
        print('Actual context:', repr(content[idx:idx+250]))

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
