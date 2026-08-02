with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Find CONTENT_TYPE_RULES definition
idx = content.find('const CONTENT_TYPE_RULES')
if idx == -1:
    print('CONTENT_TYPE_RULES not found')
else:
    # Get the definition (until the closing })
    end = content.find('\n};', idx)
    if end == -1:
        end = idx + 5000
    rules = content[idx:end+3]
    print('CONTENT_TYPE_RULES definition:')
    print(rules[:3000])  # Print first 3000 chars
