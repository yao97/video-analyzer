"""修复 web_player.html 的两个关键 bug：
1. video.src 在 onloadedmetadata 后失效 → 改用 video.onloadeddata + 保留 ObjectURL
2. 转写结果轮询逻辑缺失 → 增加 pollTranscriptionResult 函数
"""
import re

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

bug1_count = 0

# ── Bug 1: video.src 被垃圾回收 ──
# 问题: URL.createObjectURL(file) 创建的 URL 在 file 被 GC 后失效
# 修复: 把 URL 保存在全局变量，并在 onloadedmetadata 后设置 videoPreview.src
old_bug1 = """    // 显示视频预览（左侧面板）
    $('videoPreview').style.display = 'block';
    $('videoPreview').src = video.src;
    $('previewMeta').innerHTML =
      `分辨率: ${video.videoWidth}x${video.videoHeight} &nbsp;|&nbsp; 时长: ${video.duration.toFixed(1)}s<br>` +
      `文件大小: ${(file.size/1024/1024).toFixed(2)} MB &nbsp;|&nbsp; 类型: ${file.type}`;
    document.body.classList.add('video-active');"""

new_bug1 = """    // 显示视频预览（左侧面板）
    window.__previewURL = video.src;  // 防止 URL 被 GC
    $('videoPreview').style.display = 'block';
    $('videoPreview').src = window.__previewURL;
    $('videoPreview').load();  // 强制重新加载
    $('previewMeta').innerHTML =
      `分辨率: ${video.videoWidth}x${video.videoHeight} &nbsp;|&nbsp; 时长: ${video.duration.toFixed(1)}s<br>` +
      `文件大小: ${(file.size/1024/1024).toFixed(2)} MB &nbsp;|&nbsp; 类型: ${file.type}`;
    document.body.classList.add('video-active');"""

if old_bug1 in content:
    content = content.replace(old_bug1, new_bug1)
    bug1_count += 1
    print(f'Bug1 修复 #{bug1_count}')

# ── Bug 2: 转写结果轮询 ──
# 检查是否有 pollTranscription 或类似的轮询函数
has_poll = 'pollTranscription' in content or 'transcribePollTimer' in content
print(f'已有转写轮询逻辑: {has_poll}')

if not has_poll:
    print('需要添加转写轮询逻辑')
    # 在 </script> 前添加轮询函数
    poll_code = """
// ── 转写结果轮询 ──
let transcribePollTimer = null;
function pollTranscription(jobId) {
  if (transcribePollTimer) clearInterval(transcribePollTimer);
  transcribePollTimer = setInterval(async () => {
    try {
      const r = await fetch(`http://127.0.0.1:8766/api/status/${jobId}`);
      const s = await r.json();
      console.log('[转写轮询]', s.status, s.progress + '%');
      // 更新进度条
      const bar = document.getElementById('whisperProgress');
      if (bar) bar.value = s.progress;
      const pct = document.getElementById('whisperPercent');
      if (pct) pct.textContent = s.progress.toFixed(0) + '%';
      if (s.status === 'done' || s.status === 'error' || s.status === 'no_audio') {
        clearInterval(transcribePollTimer);
        transcribePollTimer = null;
        // 获取结果
        const r2 = await fetch(`http://127.0.0.1:8766/api/result/${jobId}`);
        const res = await r2.json();
        console.log('[转写结果]', res);
        if (res.status === 'done' && res.result) {
          speechResult = res.result;
          renderSpeech(res.result);
          setBadge('badgeSpeech', 'done', '已完成');
        } else {
          setBadge('badgeSpeech', 'error', res.result?.error || '失败');
        }
      }
    } catch(e) {
      console.error('[转写轮询] 错误:', e);
    }
  }, 1000);
}
"""
    # 插入到 </script> 前
    content = content.replace('</script>', poll_code + '\n  </script>')
    print('已添加转写轮询逻辑')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n修复完成，共修复 {bug1_count} 个 bug')
