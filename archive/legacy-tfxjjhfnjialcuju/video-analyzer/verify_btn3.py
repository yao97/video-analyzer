path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

result = []
# Check if button exists
if '上传新视频' in content:
    result.append('[OK] Button found')
    idx = content.find('上传新视频')
    # Get context without emoji
    ctx = content[idx-100:idx+150]
    ctx_ascii = ctx.encode('ascii', errors='replace').decode('ascii')
    result.append('Context (ascii): ' + ctx_ascii)
else:
    result.append('[FAIL] Button not found')

# Check leftPanel structure
idx2 = content.find('</div>\n<div id="rightPanel">')
if idx2 > 0:
    result.append('[OK] rightPanel found')
    ctx2 = content[idx2-150:idx2+50]
    ctx2_ascii = ctx2.encode('ascii', errors='replace').decode('ascii')
    result.append('Context: ' + ctx2_ascii)

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\verify_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(result))

print('Verification done, see verify_output.txt')
