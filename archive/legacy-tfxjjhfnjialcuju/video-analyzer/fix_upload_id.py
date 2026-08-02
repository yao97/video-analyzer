path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Fix: change uploadContainer to uploadZone for consistency
# Or change the JS to use uploadContainer

# Option 1: Change HTML id from uploadContainer to uploadZone
old = 'id="uploadContainer"'
new = 'id="uploadZone"'
if old in content:
    content = content.replace(old, new, 1)
    print('Fixed: uploadContainer -> uploadZone')
else:
    print('uploadContainer not found, checking for uploadZone...')

# Also need to fix CSS
old_css = '#uploadContainer{display:block}'
new_css = '#uploadZone{display:block}'
if old_css in content:
    content = content.replace(old_css, new_css, 1)
    print('Fixed CSS: #uploadContainer -> #uploadZone')

old_css2 = 'body.video-active #uploadContainer{display:none}'
new_css2 = 'body.video-active #uploadZone{display:none}'
if old_css2 in content:
    content = content.replace(old_css2, new_css2, 1)
    print('Fixed CSS: body.video-active #uploadContainer -> #uploadZone')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
