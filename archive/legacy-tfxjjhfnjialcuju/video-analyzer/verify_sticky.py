with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Check if sticky was added
if 'position:sticky' in content:
    print('[OK] position:sticky added to #leftPanel')
    # Show context
    idx = content.find('#leftPanel{display:none')
    if idx > 0:
        print('CSS rule:')
        print(content[idx:idx+300])
else:
    print('[FAIL] position:sticky NOT found')
