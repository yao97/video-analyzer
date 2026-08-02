"""修复 renderSpeech 中无语音内容的提示"""
import re

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换：无语音内容时的提示（两处：纯文本 和 完全无内容）
old1 = "} else if (speech?.text) {\n    $('speechTimeline').innerHTML = `<div class=\"speech-segment\"><span class=\"speech-text\">${speech.text}</span></div>`;\n  } else {"

new1 = """} else if (speech?.text) {
    $('speechTimeline').innerHTML = `<div class="speech-segment"><span class="speech-text">${speech.text}</span></div>`;
  } else if (speech?.text && !speech?.segments?.length) {
    const hint = speech.has_audio ? '（音频中未检测到人声，可能为纯音乐或环境音）' : '（无语音内容）';
    $('speechTimeline').innerHTML = `<div style="color:var(--muted);font-size:0.85rem;padding:1.2rem 0;">🎧 转写完成，但未识别到语音片段 ${hint}<br><span style="font-size:0.76rem;color:#999;">原始音频能量: ${speech.audio_features?.rms ? speech.audio_features.rms.toFixed(3) : '?'}</span></div>`;
    $('mAudioSub').textContent = '无语音';
  } else {"""

# 用正则做非贪婪替换
content = re.sub(re.escape(old1), new1, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
