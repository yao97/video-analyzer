f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'r', encoding='utf-8')
c = f.read()
f.close()

lines = c.split('\n')
# Show lines 719-726
for i in range(718, min(727, len(lines))):
    line = lines[i]
    print(f'[{i+1}] repr: {repr(line[:100])}')
    print(f'[{i+1}] ascii: {line.encode("ascii", "replace").decode("ascii")[:100]}')
