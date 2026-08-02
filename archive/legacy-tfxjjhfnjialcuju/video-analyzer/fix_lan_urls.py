with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# 1. Add TRANSCRIBE_BASE constant at the beginning of the inline script
# Find the start of the main script (after <script> tag that's not chart.js)
# Insert after: const TRANSCRIBE_BASE = window.location.protocol + '//' + window.location.hostname + ':8766';

# Find a good insertion point - after the first <script> that's not chart.js
# Actually, let's find the inline script that contains "function detectContentType"
idx = content.find('function detectContentType')
if idx > 0:
    # Go back to find the opening <script> tag
    script_start = content.rfind('<script>', 0, idx)
    if script_start > 0:
        # Insert after <script>\n
        insert_pos = script_start + len('<script>')
        const_def = '\nconst TRANSCRIBE_BASE = window.location.protocol + \'//\' + window.location.hostname + \':8766\';\n'
        content = content[:insert_pos] + const_def + content[insert_pos:]
        print('[OK] Added TRANSCRIBE_BASE constant')

# 2. Replace hardcoded URLs
# Pattern 1: 'http://127.0.0.1:8766/api/transcribe' → `${TRANSCRIBE_BASE}/api/transcribe`
old1 = "'http://127.0.0.1:8766/api/transcribe'"
new1 = "${TRANSCRIBE_BASE}/api/transcribe"
count1 = content.count(old1)
if count1 > 0:
    content = content.replace(old1, new1)
    print(f'[OK] Replaced {count1} occurrence(s) of transcribe URL')

# Pattern 2: `http://127.0.0.1:8766/api/status/${jobId}` → `${TRANSCRIBE_BASE}/api/status/${jobId}`
old2 = "`http://127.0.0.1:8766/api/status/${jobId}`"
new2 = "${TRANSCRIBE_BASE}/api/status/${jobId}"
count2 = content.count(old2)
if count2 > 0:
    content = content.replace(old2, new2)
    print(f'[OK] Replaced {count2} occurrence(s) of status URL')

# Pattern 3: `http://127.0.0.1:8766/api/result/${jobId}` → `${TRANSCRIBE_BASE}/api/result/${jobId}`
old3 = "`http://127.0.0.1:8766/api/result/${jobId}`"
new3 = "${TRANSCRIBE_BASE}/api/result/${jobId}"
count3 = content.count(old3)
if count3 > 0:
    content = content.replace(old3, new3)
    print(f'[OK] Replaced {count3} occurrence(s) of result URL')

# Also need to fix the fetch call for transcribe - it's now a template literal but was previously a string
# Find: await fetch(${TRANSCRIBE_BASE}/api/transcribe, {
# Replace with: await fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {
content = content.replace('await fetch(${TRANSCRIBE_BASE}/api/transcribe, {', 'await fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {')
print('[OK] Fixed transcribe fetch call')

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('\nDone! All hardcoded URLs replaced with dynamic TRANSCRIBE_BASE.')
