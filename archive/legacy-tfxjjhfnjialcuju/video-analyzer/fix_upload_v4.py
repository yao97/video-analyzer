with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

print("=== Fixing Upload Issue ===")

# 1. Add id="uploadZone" to the upload-zone div
old_upload = '<div class="upload-zone" onclick="document.getElementById(\'fileInput\').click()">'
new_upload = '<div class="upload-zone" id="uploadZone" onclick="document.getElementById(\'fileInput\').click()">'
if old_upload in content:
    content = content.replace(old_upload, new_upload, 1)
    print("[OK] Added id='uploadZone' to upload-zone div")
else:
    print("[WARN] upload-zone div not found, searching...")
    # Try to find it with different formatting
    idx = content.find('class="upload-zone"')
    if idx > 0:
        print(f"  Found at position {idx}")
        print(f"  Context: {content[idx:idx+150]}")
    else:
        print("[FAIL] upload-zone div not found at all")

# 2. Fix JS selector: $('uploadZone') → $('#uploadZone') or getElementById
# Actually, $() is likely a custom function or jQuery. Let's check what $() does
idx_dollar = content.find('function $(id)')
if idx_dollar > 0:
    print("[OK] $() is a custom function (gets element by ID)")
    print("  So $('uploadZone') is correct, no need to change")
else:
    # Check if jQuery is loaded
    if 'jQuery' in content or 'jquery' in content:
        print("[WARN] jQuery detected, but $('uploadZone') won't work (needs #)")
        # Fix: add # to all $('...') calls
        # Actually, let's just change the init code to use getElementById
        pass
    else:
        print("[INFO] No jQuery found, checking $() definition...")
        # Search for var $ = or const $ =
        idx_var = content.find('const $ =')
        if idx_var == -1:
            idx_var = content.find('var $ =')
        if idx_var == -1:
            idx_var = content.find('let $ =')
        if idx_var > 0:
            print(f"  $() defined at position {idx_var}")
            print(f"  Context: {content[idx_var:idx_var+100]}")
        else:
            print("[WARN] $() definition not found!")

# 3. Check the actual init code that uses uploadZone
import re
# Find all $('...') patterns
dollar_patterns = re.findall(r'\$\([\'"]([^\'"]+)[\'"]\)', content)
print(f"\nAll $('...') calls: {dollar_patterns}")

# Check if 'uploadZone' is in the list (without #)
if 'uploadZone' in dollar_patterns:
    print("[OK] Found $('uploadZone') - this is correct if $() gets element by ID")
else:
    print("[WARN] $('uploadZone') not found in JS code")

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n=== Fix Complete ===")
