f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'r', encoding='utf-8')
c = f.read()
f.close()
lines = c.split('\n')

print(f'Total lines: {len(lines)}')
print()

print('=== Tab Buttons ===')
for i, line in enumerate(lines):
    if 'class="tab"' in line and 'onclick' in line:
        print(f'[{i+1}] {line.strip()[:120]}')

print()
print('=== Tab Content Divs ===')
for i, line in enumerate(lines):
    if 'id="tab' in line and ('Content' in line or 'Panel' in line):
        print(f'[{i+1}] {line.strip()[:120]}')

print()
print('=== render* Functions ===')
for i, line in enumerate(lines):
    if line.strip().startswith('function render') or line.strip().startswith('async function render'):
        print(f'[{i+1}] {line.strip()[:100]}')

print()
print('=== analysisResult fields ===')
for i, line in enumerate(lines):
    if 'analysisResult = {' in line or 'analysisResult=' in line:
        for j in range(i, min(i+20, len(lines))):
            print(f'[{j+1}] {lines[j].strip()[:120]}')
        break
