with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

print("=== Fixing fetch() syntax ===")

# Fix 1: transcribe fetch call
old1 = 'await fetch(${TRANSCRIBE_BASE}/api/transcribe`, {'
new1 = 'await fetch(`${TRANSCRIBE_BASE}/api/transcribe`, {'
if old1 in content:
    content = content.replace(old1, new1, 1)
    print("[OK] Fixed transcribe fetch call")
else:
    print("[INFO] transcribe fetch call not found (already fixed?)")

# Fix 2: status fetch call  
old2 = 'fetch(${TRANSCRIBE_BASE}/api/status/${jobId}`);'
new2 = 'fetch(`${TRANSCRIBE_BASE}/api/status/${jobId}`);'
if old2 in content:
    content = content.replace(old2, new2, 1)
    print("[OK] Fixed status fetch call")
else:
    print("[INFO] status fetch call not found (already fixed?)")

# Fix 3: result fetch call
old3 = 'fetch(${TRANSCRIBE_BASE}/api/result/${jobId}`);'
new3 = 'fetch(`${TRANSCRIBE_BASE}/api/result/${jobId}`);'
if old3 in content:
    content = content.replace(old3, new3, 1)
    print("[OK] Fixed result fetch call")
else:
    print("[INFO] result fetch call not found (already fixed?)")

# Also check for any remaining broken patterns
import re
broken = re.findall(r'fetch\(\$ \{[^`]*\'', content)
if broken:
    print(f"\n[WARN] Found {len(broken)} potentially broken fetch calls:")
    for b in broken[:3]:
        print(f"  {b[:80]}")
else:
    print("\n[OK] No broken fetch() calls found")

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n=== Fix complete ===")
print("Please Ctrl+F5 to refresh the page.")
