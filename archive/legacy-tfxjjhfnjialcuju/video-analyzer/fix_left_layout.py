"""Fix layout: video on left (fixed), analysis on right. Rewrite the body structure."""
import re

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ── 1. Add CSS for fixed left panel layout ──
new_css = """
/* Fixed left video panel */
body.video-active header {
  margin-left: 360px !important;
}
body.video-active .container {
  margin-left: 360px !important;
  max-width: calc(1400px - 360px) !important;
}
#leftPanel {
  position: fixed !important;
  left: 0; top: 0;
  width: 360px; height: 100vh;
  overflow-y: auto;
  z-index: 999;
  padding: 1rem;
  background: var(--bg);
  border-right: 1px solid var(--border);
}
/* Hide scrollbar on left panel */
#leftPanel::-webkit-scrollbar { width: 3px; }
#leftPanel::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
/* mainLayout should not be flex (leftPanel is fixed) */
#mainLayout {
  display: none;
  padding: 0;
}
body.video-active #mainLayout {
  display: block !important;
}
"""
content = content.replace('</style>', new_css + '</style>')

# ── 2. Fix leftPanel inline style (remove sticky, CSS handles it) ──
old_left_style = 'style="flex-shrink:0; width:360px; max-width:40vw; position:sticky; top:1rem;"'
new_left_style = 'style="width:100%;"'
content = content.replace(old_left_style, new_left_style)

# ── 3. Fix rightPanel (remove flex:1 since leftPanel is fixed) ──
content = content.replace('id="rightPanel" style="flex:1; min-width:320px;"', 
                          'id="rightPanel" style="min-width:0;"')

# ── 4. Update JS: add video-active class to body ──
old_js = "$('mainLayout').style.display = 'flex';"
new_js = "    document.body.classList.add('video-active');\n    $('mainLayout').style.display = 'block';"
content = content.replace(old_js, new_js)

# ── 5. On re-upload, keep video-active class (don't remove it) ──
#     The leftPanel already shows "更换视频" upload zone, so no need to toggle

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Layout fixed: video on left (fixed), analysis on right')
print('CSS added for body.video-active')
print('JS updated to add video-active class')
