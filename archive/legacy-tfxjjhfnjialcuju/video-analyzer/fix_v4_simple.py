with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Simple fix: add backtick before ${TRANSCRIBE_BASE}
old = 'fetch(${TRANSCRIBE_BASE}/'
new = 'fetch(`${TRANSCRIBE_BASE}/'

count = content.count(old)
if count > 0:
    content = content.replace(old, new)
    print(f'Fixed {count} occurrence(s) of fetch($...')

# Also fix the transcribe call
old2 = 'await fetch(${TRANSCRIBE_BASE}/api/transcribe`, {'
new2 = 'await fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {'
if old2 in content:
    content = content.replace(old2, new2, 1)
    print('Fixed transcribe fetch call')

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done. Verifying...')

# Verify
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    verified = f.read()

if 'fetch(${TRANSCRIBE_BASE}/' in verified:
    print('FAIL: broken pattern still exists')
else:
    print('OK: no broken fetch() calls')

# Show correct pattern
import re
matches = re.findall(r'fetch\(`\$\{TRANSCRIBE_BASE\}[^`]{0,80}`', verified)
print(f'Found {len(matches)} correct fetch() calls')
