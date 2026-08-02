with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

print("=== Final Upload Fix ===")

# 1. Remove id="uploadZone" from container div (if present)
old_container = '<div class="container" id="uploadZone">'
new_container = '<div class="container">'
if old_container in content:
    content = content.replace(old_container, new_container, 1)
    print("[OK] Removed id='uploadZone' from container div")
else:
    print("[INFO] id='uploadZone' not on container div (already fixed)")

# 2. Ensure upload-zone div has id="uploadZone"
old_upload = '<div class="upload-zone" onclick="document.getElementById(\'fileInput\').click()">'
new_upload = '<div class="upload-zone" id="uploadZone" onclick="document.getElementById(\'fileInput\').click()">'
if old_upload in content:
    content = content.replace(old_upload, new_upload, 1)
    print("[OK] Added id='uploadZone' to upload-zone div")
else:
    # Check if it already has the ID
    if 'id="uploadZone"' in content and 'class="upload-zone" id="uploadZone"' in content:
        print("[OK] upload-zone div already has id='uploadZone'")
    else:
        print("[WARN] upload-zone div structure unexpected")
        # Find it
        idx = content.find('class="upload-zone"')
        if idx > 0:
            print(f"  Found at {idx}: {content[idx:idx+150]}")

# 3. Verify no duplicate IDs
import re
ids = re.findall(r'id="([^"]+)"', content)
dupes = [id for id in ids if ids.count(id) > 1]
if dupes:
    print(f"\n[WARN] Duplicate IDs found: {set(dupes)}")
else:
    print("\n[OK] No duplicate IDs")

# 4. Verify event listeners are attached correctly
# Check init code
init_start = content.find('// ── Init ──')
if init_start > 0:
    init_code = content[init_start:init_start+2000]
    if 'uploadZone' in init_code and 'addEventListener' in init_code:
        print("[OK] Event listeners should be attached in init code")
        # Show the relevant code
        idx_uz = init_code.find('uploadZone')
        if idx_uz > 0:
            print("  Init code context:")
            print(init_code[idx_uz-100:idx_uz+200].replace('\n', '\n  '))
    else:
        print("[FAIL] uploadZone event listeners NOT found in init code!")

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n=== Fix Complete ===")
print("Please Ctrl+F5 to refresh, then try uploading again.")
print("If still broken, open browser console (F12) and share any errors.")
