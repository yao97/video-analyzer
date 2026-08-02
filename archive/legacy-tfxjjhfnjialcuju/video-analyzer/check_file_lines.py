f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'r', encoding='utf-8')
c = f.read()
f.close()
lines = c.split('\n')
print(f'Total lines: {len(lines)}')
for i in range(max(0, len(lines)-20), len(lines)):
    print(f'[{i+1}] {repr(lines[i][:100])}')
