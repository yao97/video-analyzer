path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Find scoreContentType function
idx = content.find('function scoreContentType')
if idx > 0:
    # Get the function body
    func_end = content.find('\n}\n', idx)
    if func_end == -1:
        func_end = content.find('\n}\n', idx + 100)
    print('scoreContentType function:')
    print(content[idx:func_end+4])
    print('\n\n=== Function end ===')
else:
    print('scoreContentType not found')
