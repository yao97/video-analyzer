with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Search for detectContentType
idx = content.find('function detectContentType')
if idx > 0:
    print('FOUND: function detectContentType at position', idx)
    print('Context:')
    print(content[idx:idx+500])
else:
    print('NOT FOUND: function detectContentType')
    print('Searching for "detectContentType" (any occurrence)...')
    idx2 = content.find('detectContentType')
    if idx2 > 0:
        print('Found reference at position', idx2)
        print('Context:', content[idx2-50:idx2+200])
    else:
        print('No reference to detectContentType found at all!')
        print('This means the function is missing from the file.')
