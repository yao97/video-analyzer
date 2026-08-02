with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Check if label field exists in CONTENT_TYPE_RULES
import re
# Find CONTENT_TYPE_RULES block
idx = content.find('const CONTENT_TYPE_RULES')
if idx > 0:
    # Get first 2000 chars
    block = content[idx:idx+2000]
    if 'label:' in block:
        print('[OK] label field found in CONTENT_TYPE_RULES')
        # Show context around label
        label_idx = block.find('label:')
        print('Context:', block[label_idx-50:label_idx+100])
    else:
        print('[FAIL] label field NOT found in CONTENT_TYPE_RULES')
    
    if 'icon:' in block:
        print('[OK] icon field found')
    else:
        print('[FAIL] icon field NOT found')
    
    if 'color:' in block:
        print('[OK] color field found')
    else:
        print('[FAIL] color field NOT found')
