f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'r', encoding='utf-8')
c = f.read()
f.close()
lines = c.split('\n')
print(f'Total lines: {len(lines)}')
for i, line in enumerate(lines):
    if '@app.route' in line or 'def ' in line and not line.strip().startswith('#'):
        print(f'[{i+1}] {line.strip()[:100]}')
