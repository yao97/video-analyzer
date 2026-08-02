with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

print("=== Fix fetch() backticks ===")

# The broken pattern: fetch(${TRANSCRIBE_BASE}/  (missing opening backtick)
# The correct pattern: fetch(`${TRANSCRIBE_BASE}/

old = 'fetch(${TRANSCRIBE_BASE}/'
new = 'fetch(`${TRANSCRIBE_BASE}/'

count = content.count(old)
if count > 0:
    content = content.replace(old, new)
    print(f"[OK] Fixed {count} occurrence(s) of fetch(${{TRANSCRIBE_BASE}/ → fetch(`${{TRANSCRIBE_BASE}}/")
else:
    print("[INFO] Broken pattern not found, checking alternative patterns...")
    # Maybe the file has different formatting
    if '${TRANSCRIBE_BASE}' in content:
        # Find all occurrences of TRANSCRIBE_BASE
        import re
        occurrences = [m.start() for m in re.finditer(r'\$\{TRANSCRIBE_BASE\}', content)]
        print(f"[INFO] Found {len(occurrences)} occurrences of ${{TRANSCRIBE_BASE}}")
        for pos in occurrences[:3]:
            print(f"  Position {pos}: {content[pos-30:pos+50].replace(chr(10), ' ')}")

# Also check for the upload fetch call (it has different formatting)
if 'await fetch(${TRANSCRIBE_BASE}/api/transcribe`, {' in content:
    content = content.replace('await fetch(${TRANSCRIBE_BASE}/api/transcribe`, {',
                            'await fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {')
    print("[OK] Fixed transcribe fetch call")

# Write back
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
print("\n=== Verification ===")
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    verified = f.read()

# Check if the broken pattern still exists
if 'fetch(${TRANSCRIBE_BASE}/' in verified:
    print("[FAIL] Broken pattern still exists!")
else:
    print("[OK] No broken fetch() calls found")

# Show the fixed lines
import re
fixed = re.findall(r'fetch\(`\$\{TRANSCRIBE_BASE\}[^`]*`', verified)
print(f"\n[INFO] Found {len(fixed)} correctly formatted fetch() calls:")
for f in fixed[:3]:
    print(f"  {f}")
