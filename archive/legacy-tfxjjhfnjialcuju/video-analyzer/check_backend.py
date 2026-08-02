f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'r', encoding='utf-8')
c = f.read()
f.close()
lines = c.split('\n')
print(f'Total lines: {len(lines)}')
print('analyze-copy:', '/api/analyze-copy' in c)
print('call_llm_analyze:', 'call_llm_analyze' in c)
print('ANALYZE_PROMPT:', 'ANALYZE_PROMPT' in c)
print()
for i, line in enumerate(lines[-5]):
    print(f'[{len(lines)-4}] last lines...')
    break
for i in range(max(0,len(lines)-8), len(lines)):
    print(f'[{i+1}] {repr(lines[i][:80])}')
