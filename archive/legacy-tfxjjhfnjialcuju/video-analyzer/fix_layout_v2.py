"""Rewrite web_player.html with clean left/right flex layout.
Left: video preview (fixed width 360px, sticky)
Right: all analysis tabs
"""
import re

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ── Replace the broken mainLayout structure ──
# Find: <div id="mainLayout" ...> through </div><!-- /rightPanel --> ... </div><!-- /mainLayout -->
# This is complex. Instead, let me just fix the CSS and JS so the current structure works.

# SIMPLE FIX: Use flexbox on .container when video is active
# Replace the broken CSS approach with a simple one:

new_css = """
/* ── Video-active layout: flex container ── */
body.video-active .container {
  display: flex !important;
  gap: 1.5rem;
  max-width: 100% !important;
  padding: 1rem 1.5rem !important;
  align-items: flex-start;
}
body.video-active header {
  display: none !important;
}
/* Left: video panel */
body.video-active #leftPanel {
  display: block !important;
  width: 340px !important;
  flex-shrink: 0 !important;
  position: sticky !important;
  top: 1rem !important;
}
/* Right: analysis content */
body.video-active #rightPanel {
  display: block !important;
  flex: 1 !important;
  min-width: 0 !important;
}
/* Hide mainLayout wrapper (we don't need it) */
#mainLayout { display: none !important; }
body.video-active #mainLayout { display: flex !important; flex-direction: row !important; width: 100% !important; }
"""

# Insert before </style>
content = content.replace('</style>', new_css + '\n  </style>')

# ── Fix JS: when video loads, add video-active to body and show leftPanel ──
old_js_block = """    // 显示视频预览（左侧面板）
    $('videoPreview').style.display = 'block';
    $('videoPreview').src = video.src;
    $('previewMeta').innerHTML =
      `分辨率: ${video.videoWidth}x${video.videoHeight} &nbsp;|&nbsp; 时长: ${video.duration.toFixed(1)}s<br>` +
      `文件大小: ${(file.size/1024/1024).toFixed(2)} MB &nbsp;|&nbsp; 类型: ${file.type}`;
        document.body.classList.add('video-active');
    $('mainLayout').style.display = 'block';"""

new_js_block = """    // 显示视频预览（左侧面板）
    $('videoPreview').style.display = 'block';
    $('videoPreview').src = video.src;
    $('previewMeta').innerHTML =
      `分辨率: ${video.videoWidth}x${video.videoHeight} &nbsp;|&nbsp; 时长: ${video.duration.toFixed(1)}s<br>` +
      `文件大小: ${(file.size/1024/1024).toFixed(2)} MB &nbsp;|&nbsp; 类型: ${file.type}`;
    document.body.classList.add('video-active');
    $('mainLayout').style.display = 'flex';"""

if old_js_block in content:
    content = content.replace(old_js_block, new_js_block)
    print('Fixed JS: video preview block')
else:
    print('WARNING: Could not find JS block to replace')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Layout CSS + JS updated')
print('Now leftPanel will be sticky at 340px, rightPanel takes remaining space')
