with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Replace hardcoded 127.0.0.1:8766 with dynamic host
old_api = 'http://127.0.0.1:8766/api/transcribe'
new_api = 'http://' + window.location.hostname + ':8766/api/transcribe'
# Actually, we need to do this in JS, not Python string replacement
# Let's find the fetch calls and replace the base URL

import re

# Find all fetch calls to 127.0.0.1:8766 and replace with dynamic base
# Pattern: fetch('http://127.0.0.1:8766/...')
# Replace with: fetch(`http://${window.location.hostname}:8766/...`)

# Actually simpler: define a global const at the top of the script
# Insert after <script> tag that contains the main JS

# Find the start of the main inline script (after chart.js)
# We'll add a global TRANSCRIBE_BASE constant

# First, let's find and replace all hardcoded URLs
urls = [
    ('http://127.0.0.1:8766/api/transcribe', '`${TRANSCRIBE_BASE}/api/transcribe`'),
    ('http://127.0.0.1:8766/api/status/', '`${TRANSCRIBE_BASE}/api/status/`'),
    ('http://127.0.0.1:8766/api/result/', '`${TRANSCRIBE_BASE}/api/result/`'),
]

# Actually, the URL is split across multiple lines in fetch()
# Let's search for the actual patterns in the file
idx1 = content.find('http://127.0.0.1:8766')
if idx1 > 0:
    print(f'Found hardcoded URL at position {idx1}')
    print('Context:', content[idx1-50:idx1+100])
else:
    print('No hardcoded 127.0.0.1:8766 found')
    # Maybe it's already using a variable?
    if 'TRANSCRIBE_BASE' in content:
        print('TRANSCRIBE_BASE already defined')
    else:
        print('Need to add TRANSCRIBE_BASE')
