with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Find all occurrences of hardcoded 127.0.0.1:8766
idx = 0
count = 0
while True:
    idx = content.find('127.0.0.1:8766', idx)
    if idx == -1:
        break
    count += 1
    print(f'Found at position {idx}:')
    print('  Context:', content[max(0,idx-60):idx+80].replace('\n', ' '))
    idx += 1

print(f'\nTotal occurrences: {count}')

# Also check if TRANSCRIBE_BASE is already defined
if 'TRANSCRIBE_BASE' in content:
    print('[INFO] TRANSCRIBE_BASE already exists in file')
else:
    print('[INFO] Need to add TRANSCRIBE_BASE constant')
