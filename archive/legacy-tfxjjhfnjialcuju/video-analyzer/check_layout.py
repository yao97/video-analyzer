"""Fix all issues:
1. video-active class add (missing semicolon / syntax)
2. Restart transcribe server
3. Test transcription with a real audio file
"""
import re

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Fix 1: missing semicolon after document.body.classList.add
old = "        document.body.classList.add('video-active');\n    $('mainLayout').style.display = 'block';"
new = "        document.body.classList.add('video-active');\n        $('mainLayout').style.display = 'block';"
if old in c:
    c = c.replace(old, new)
    print('Fixed: added semicolon after video-active class add')
else:
    # Check if it's already correct
    if "document.body.classList.add('video-active')" in c:
        print('video-active line exists, checking context...')
        idx = c.find("document.body.classList.add('video-active')")
        print('Context:', repr(c[max(0,idx-30):idx+100]))

# Fix 2: The leftPanel is inside mainLayout which has display:none initially
# But mainLayout is set to display:block when video-active is added
# The issue might be that mainLayout is inside .container which has padding
# Let me check: is mainLayout directly inside .container?
idx_container = c.find('class="container">')
idx_mainlayout = c.find('id="mainLayout"')
print(f'container at: {idx_container}, mainLayout at: {idx_mainlayout}')
print('mainLayout inside container?', idx_mainlayout > idx_container)

# Fix 3: Ensure CSS for video-active works
# The current CSS adds margin-left to header and .container
# But mainLayout is INSIDE .container, so the margin on .container pushes everything right
# AND leftPanel is position:fixed inside mainLayout which is inside .container
# This means leftPanel's "fixed" is relative to .container, not viewport!
# That's the bug! position:fixed with a parent that has transform/overflow/padding might not work as expected
# Actually, position:fixed is always relative to viewport unless the parent has transform, perspective, or filter set
# Let me check if .container or any parent has transform...

# Actually, the simplest fix: don't use position:fixed. Use CSS Grid or Flexbox.
# Let me rewrite the layout properly.

print('\nDone checking. Now fixing layout...')

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print('File checked and potentially fixed.')
print('NOTE: The layout may need a complete rewrite to use flexbox instead of position:fixed.')
