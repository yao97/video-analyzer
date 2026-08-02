"""把页面布局改为：左侧视频预览固定，右侧分析结果"""
import re

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在 <body> 开头、header 之后插入左右分栏容器
# 找到 <!-- Upload --> 前面，插入 layout 容器
old_layout_start = """  <!-- Upload -->
  <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
    <div class="icon-big">&#128229;</div>
    <h2>点击上传视频文件</h2>
    <p>支持 MP4 / MOV / AVI / MKV / WebM &nbsp;|&nbsp; 画面+语音全分析 &nbsp;|&nbsp; 本地处理</p>
    <input type="file" id="fileInput" accept="video/mp4,video/mov,video/avi,video/x-matroska,video/webm">
  </div>

  <!-- Video Preview -->
  <div id="videoPreviewSection" class="hidden" style="margin-bottom:1.2rem;">
    <div style="display:flex;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
      <video id="videoPreview" controls style="max-height:280px;border-radius:10px;flex-shrink:0;background:#000;" preload="metadata"></video>
      <div style="flex:1;min-width:200px;">
        <div style="font-size:0.92rem;font-weight:700;margin-bottom:0.4rem;" id="previewFileName"></div>
        <div style="font-size:0.76rem;color:var(--muted);line-height:1.8;" id="previewMeta"></div>
      </div>
    </div>
  </div>"""

new_layout_start = """  <!-- Main Layout: 左侧视频 | 右侧分析 -->
  <div id="mainLayout" style="display:none; gap:1.5rem; align-items:flex-start; padding:1.5rem 2rem; flex-wrap:wrap;">
    <!-- Left: Video + Upload -->
    <div id="leftPanel" style="flex-shrink:0; width:360px; max-width:40vw; position:sticky; top:1rem;">
      <div class="upload-zone" onclick="document.getElementById('fileInput').click()" style="padding:1rem; font-size:0.85rem; margin-bottom:1rem;">
        <div class="icon-big" style="font-size:2rem;">&#128229;</div>
        <h2 style="font-size:1rem;">更换视频</h2>
        <p style="font-size:0.72rem;">点击此处上传新视频</p>
        <input type="file" id="fileInput" accept="video/mp4,video/mov,video/avi,video/x-matroska,video/webm">
      </div>
      <video id="videoPreview" controls style="width:100%; border-radius:10px; background:#000; display:none;"></video>
      <div id="previewMeta" style="font-size:0.72rem; color:var(--muted); margin-top:0.5rem; line-height:1.8;"></div>
    </div>
    <!-- Right: Analysis Tabs -->
    <div id="rightPanel" style="flex:1; min-width:320px;">
"""

# 在文件里找到旧的上传区域，替换为新布局
content = content.replace(old_layout_start, new_layout_start)

# 2. 在 </body> 前关闭 rightPanel 和 mainLayout 的 div
old_end = '  <!-- Footer -->\n  <div class="footer">&copy; 2026 Video Content Analyzer &nbsp;·&nbsp; 本地 AI 分析 &nbsp;·&nbsp; 数据不上传</div>\n</body>'
new_end = '    </div><!-- /rightPanel -->\n  </div><!-- /mainLayout -->\n  <!-- Footer -->\n  <div class="footer">&copy; 2026 Video Content Analyzer &nbsp;·&nbsp; 本地 AI 分析 &nbsp;·&nbsp; 数据不上传</div>\n</body>'
content = content.replace(old_end, new_end)

# 3. 把所有 analysis-tabs / tab-content 相关的顶层 div 包进 rightPanel（已经在上面处理了）
# 4. 修改 JS：上传完成后显示 mainLayout，隐藏上传 zone
#    找到 processFile 函数里显示预览的代码，改为：
old_js_preview = """    // 显示视频预览\n    $('videoPreview').src = video.src;\n    $('previewFileName').textContent = file.name;\n    $('previewMeta').innerHTML =\n      `分辨率: ${video.videoWidth}x${video.videoHeight} &nbsp;|&nbsp; 时长: ${video.duration.toFixed(1)}s<br>` +\n      `文件大小: ${(file.size/1024/1024).toFixed(2)} MB &nbsp;|&nbsp; 类型: ${file.type}`;\n    show('videoPreviewSection');"""

new_js_preview = """    // 显示视频预览（左侧面板）\n    $('videoPreview').style.display = 'block';\n    $('videoPreview').src = video.src;\n    $('previewMeta').innerHTML =\n      `分辨率: ${video.videoWidth}x${video.videoHeight} &nbsp;|&nbsp; 时长: ${video.duration.toFixed(1)}s<br>` +\n      `文件大小: ${(file.size/1024/1024).toFixed(2)} MB &nbsp;|&nbsp; 类型: ${file.type}`;\n    $('mainLayout').style.display = 'flex';\n    // 隐藏顶部的上传提示（如果有）\n    document.querySelectorAll('.upload-zone').forEach(z => z.style.display = 'none');"""

content = content.replace(old_js_preview, new_js_preview)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done - layout changed to left/right')
