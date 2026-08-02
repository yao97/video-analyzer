f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'r', encoding='utf-8')
c = f.read()
f.close()
lines = c.split('\n')
# show last 100 lines to see how file ends
for i in range(max(0, len(lines)-30), len(lines)):
    print(f'[{i+1}] {repr(lines[i][:100])}')
