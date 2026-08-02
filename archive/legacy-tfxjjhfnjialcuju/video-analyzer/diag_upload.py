with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Check upload zone configuration
print("=== Upload Zone Diagnostics ===")

# 1. Check if uploadZone ID exists
if 'id="uploadZone"' in content:
    print("[OK] uploadZone ID found")
    # Show context
    idx = content.find('id="uploadZone"')
    print("  Context:", content[idx-100:idx+200].replace('\n', ' '))
else:
    print("[FAIL] uploadZone ID NOT found")

# 2. Check if fileInput ID exists
if 'id="fileInput"' in content:
    print("[OK] fileInput ID found")
else:
    print("[FAIL] fileInput ID NOT found")

# 3. Check drag-drop event listeners
import re
# Find addEventListener calls
listeners = re.findall(r'\.addEventListener\([\'"](\w+)[\'"]', content)
print(f"\nEvent listeners found: {listeners}")

# 4. Check for JavaScript errors (common ones)
if '$(\'uploadZone\')' in content:
    print("\n[WARN] Found $('uploadZone') - should be $('#uploadZone')")
if '$(\'fileInput\')' in content:
    print("[WARN] Found $('fileInput') - should be $('#fileInput')")

# 5. Check if processFile function exists
if 'function processFile' in content:
    print("\n[OK] processFile function found")
else:
    print("\n[FAIL] processFile function NOT found")

# 6. Check for syntax errors (unmatched brackets)
open_brackets = content.count('{')
close_brackets = content.count('}')
print(f"\nBracket balance: {{ = {open_brackets}, }} = {close_brackets}, diff = {open_brackets - close_brackets}")

print("\n=== End Diagnostics ===")
