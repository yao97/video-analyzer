with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

print("=== Fixing fetch() calls ===")

# Fix all fetch calls that have ${TRANSCRIBE_BASE} without backticks
# Pattern: fetch(${TRANSCRIBE_BASE}/...) → fetch(`${TRANSCRIBE_BASE}/...`)

import re

# Find all fetch calls
fetch_pattern = r'fetch\(\$ \{TRANSCRIBE_BASE\}([^)]*)\)'
# Actually, the pattern is simpler: fetch(${TRANSCRIBE_BASE}/...)
# which should be: fetch(`${TRANSCRIBE_BASE}/...`)

old = "fetch(${TRANSCRIBE_BASE}"
new = "fetch(`${TRANSCRIBE_BASE}"

count = content.count(old)
if count > 0:
    content = content.replace(old, new)
    print(f"[OK] Fixed {count} occurrence(s) of fetch(${{TRANSCRIBE_BASE} → fetch(`${{TRANSCRIBE_BASE}`")

# Also check for the closing backtick - the replacement above adds opening backtick + ${
# but we also need to ensure the closing backtick is before the closing paren
# Let's check the context around each fix

# Actually, let's just do a comprehensive fix:
# Replace: fetch(${TRANSCRIBE_BASE}/XXX) → fetch(`${TRANSCRIBE_BASE}/XXX`)
# This is a simple string replacement

fixes = [
    ("fetch(${TRANSCRIBE_BASE}/api/transcribe`, {",
     "fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {"),
    ("fetch(${TRANSCRIBE_BASE}/api/status/${jobId}`);",
     "fetch(`${TRANSCRIBE_BASE}/api/status/${jobId}`);"),
    ("fetch(${TRANSCRIBE_BASE}/api/result/${jobId}`);",
     "fetch(`${TRANSCRIBE_BASE}/api/result/${jobId}`);"),
]

for old_str, new_str in fixes:
    if old_str in content:
        content = content.replace(old_str, new_str, 1)
        print(f"[OK] Fixed: {old_str[:60]}...")
    else:
        print(f"[INFO] Not found: {old_str[:60]}...")

# Also fix the transcribe fetch call (it's different formatting)
# The transcribe call was originally:
# await fetch(${TRANSCRIBE_BASE}/api/transcribe, {
# But it should be:
# await fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {
if 'await fetch(${TRANSCRIBE_BASE}/api/transcribe, {' in content:
    content = content.replace('await fetch(${TRANSCRIBE_BASE}/api/transcribe, {',
                                'await fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {')
    print("[OK] Fixed transcribe fetch call")

# Write back
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
print("\n=== Verification ===")
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    verified = f.read()

# Check for remaining broken fetch calls
import re
broken = re.findall(r'fetch\(\$ \{[^`]*\'', verified)
if broken:
    print(f"[FAIL] Found {len(broken)} potentially broken fetch calls:")
    for b in broken[:3]:
        print(f"  {b}")
else:
    print("[OK] No broken fetch calls found")

# Show the fixed lines
idx = verified.find('${TRANSCRIBE_BASE}')
if idx > 0:
    print(f"\n[INFO] TRANSCRIBE_BASE usage at position {idx}:")
    print(f"  Context: {verified[idx-30:idx+80].replace(chr(10), ' ')}")
