path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'async function processFile' in line:
        print(f'L{i+1}: {line.strip()[:80]}')
        # Print context
        for j in range(max(0, i-2), min(len(lines), i+5)):
            mark = '>>> ' if j == i else '    '
            print(f'{mark}L{j+1}: {lines[j].rstrip()[:100]}')
        break
else:
    print('processFile not found')
