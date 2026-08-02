"""最小化验证页面：只做一件事——上传视频后在左侧显示预览"""
import http.server, threading, os

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>视频预览测试</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: sans-serif; background: #0f1117; color: #e2e8f0; height: 100vh; }
body.has-video { display: flex; }
#left { display: none; width: 360px; padding: 1rem; background: #1a1d27; flex-shrink: 0; }
body.has-video #left { display: block; }
#left video { width: 100%; border-radius: 8px; }
#right { flex: 1; padding: 2rem; }
.upload-zone { border: 2px dashed #6366f1; border-radius: 12px; padding: 3rem; text-align: center; cursor: pointer; }
.upload-zone:hover { background: #1a1d27; }
</style>
</head>
<body>
<div id="left">
  <video id="preview" controls></video>
  <div id="meta" style="margin-top:0.5rem;font-size:0.75rem;color:#6b7084;"></div>
</div>
<div id="right">
  <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
    <p>📁 点击上传视频</p>
    <p style="font-size:0.75rem;color:#6b7084;margin-top:0.5rem;">支持 MP4 / MOV / AVI</p>
  </div>
  <input type="file" id="fileInput" accept="video/*" style="display:none" onchange="loadVideo(this.files[0])">
</div>
<script>
function loadVideo(file) {
  if (!file) return;
  const url = URL.createObjectURL(file);
  const video = document.getElementById('preview');
  video.src = url;
  video.onloadedmetadata = () => {
    document.getElementById('meta').innerHTML =
      '分辨率: ' + video.videoWidth + 'x' + video.videoHeight + '<br>' +
      '时长: ' + video.duration.toFixed(1) + 's<br>' +
      '大小: ' + (file.size/1024/1024).toFixed(2) + 'MB';
    document.body.classList.add('has-video');
    URL.revokeObjectURL(url);
  };
}
</script>
</body>
</html>"""

DIR = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer'

with open(os.path.join(DIR, 'test_preview_minimal.html'), 'w', encoding='utf-8') as f:
    f.write(HTML)

print('已写入 test_preview_minimal.html')
print('请访问: http://127.0.0.1:8765/test_preview_minimal.html')
print('这个页面只做一件事：上传视频后在左侧显示预览')
print('如果这个页面能正常预览，说明原页面的问题是 JS 复杂度太高导致冲突')
print('如果不能预览，说明是浏览器/系统问题')
