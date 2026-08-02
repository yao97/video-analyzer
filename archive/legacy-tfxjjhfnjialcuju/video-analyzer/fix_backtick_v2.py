with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

print("=== Fix template literal backticks in fetch() ===")

# The issue: fetch(`${TRANSCRIBE_BASE}/api/status/${jobId}); 
# should be:     fetch(`${TRANSCRIBE_BASE}/api/status/${jobId}`);
# The closing backtick is missing before the closing paren.

# Fix all three fetch calls
fixes = [
    # pollTranscribeResult - status API
    ("fetch(`${TRANSCRIBE_BASE}/api/status/${jobId});",
     "fetch(`${TRANSCRIBE_BASE}/api/status/${jobId}`);"),
    # pollTranscribeResult - result API  
    ("fetch(`${TRANSCRIBE_BASE}/api/result/${jobId});",
     "fetch(`${TRANSCRIBE_BASE}/api/result/${jobId}`);"),
    # startTranscription - transcribe API (POST)
    ("fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {",
     "fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {"),
]

for old, new in fixes:
    if old in content:
        content = content.replace(old, new, 1)
        print(f"[OK] Fixed: {old[:70]}...")
    else:
        print(f"[INFO] Not found: {old[:70]}...")

# Also do a general fix: find all fetch(`${...}) patterns and add missing backtick
import re
# Pattern: fetch(`${...})  (missing backtick before ))
broken_pattern = r'fetch\(\`\$\{TRANSCRIBE_BASE\}[^`]*\}\)'
broken = re.findall(broken_pattern, content)
if broken:
    print(f"\n[WARN] Found {len(broken)} potentially broken fetch calls (missing backtick before )):")
    for b in broken:
        print(f"  {b}")
        # Fix: add backtick before the closing paren
        fixed = b.replace('})', '}`)')
        content = content.replace(b, fixed, 1)
        print(f"  Fixed to: {fixed}")
else:
    print("\n[OK] No broken template literals found")

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)

# Final verification
print("\n=== Final Verification ===")
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    verified = f.read()

# Check line 1027 specifically
lines = verified.split('\n')
if len(lines) >= 1027:
    print(f"Line 1027: {lines[1026]}")

# Check for any remaining broken patterns
broken_now = re.findall(r'fetch\(\`\$\{TRANSCRIBE_BASE\}[^`]*\}\)', verified)
if broken_now:
    print(f"\n[FAIL] Still {len(broken_now)} broken fetch calls!")
else:
    print("\n[OK] All fetch() calls properly formatted")
