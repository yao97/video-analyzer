path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Insert button before closing </div> of #leftPanel
# The pattern: speechPreviewText closing + speechPreviewSection closing + leftPanel closing
old = (
    '<div id="speechPreviewText" style="font-size:0.78rem;color:#6b7084;">等待分析...</div>\n'
    '  </div>\n'
    '  </div>\n'
    '  <div id="rightPanel">'
)
# Note: need to check actual whitespace. Let me search more flexibly.

# Actually, let me find the exact position of leftPanel closing tag
import re
# Find the structure: #leftPanel opening, then eventually its closing
left_panel_close_pattern = r'( *)(</div>\s*<div id="rightPanel">)'
# But need to make sure it's the one closing leftPanel

# Simpler: find the speechPreviewSection end, then insert button before leftPanel closes
idx = content.find('<div id="speechPreviewText"')
if idx == -1:
    print("ERROR: speechPreviewText not found")
else:
    # Find the closing </div> of speechPreviewSection, then the next </div> closes leftPanel
    # speechPreviewSection opening
    section_start = content.find('<div id="speechPreviewSection"', idx-200)
    if section_start == -1:
        # try different offset
        section_start = content.rfind('<div id="speechPreviewSection"', 0, idx)
    print(f"speechPreviewSection starts at: {section_start}")
    
    # Find matching closing </div> for speechPreviewSection  
    # Actually the HTML is minified-ish, let me just find the pattern:
    # ...</div> (close speechPreviewText)
    #   </div> (close speechPreviewSection)
    #   </div> (close leftPanel)
    #   <div id="rightPanel">
    
    # Let me search for the exact text block
    block = content[section_start:section_start+500]
    print("Block context:")
    print(repr(block))
