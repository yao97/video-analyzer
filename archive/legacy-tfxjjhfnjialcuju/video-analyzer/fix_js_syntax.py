"""修复 web_player.html 中 processFile 函数的 JS 语法错误"""
import re

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 错误1: Math.min(t, duration - 0.01) 少了右括号
# 原代码: video.currentTime = Math.min(t, duration - 0.01);
# 应该是: video.currentTime = Math.min(t, duration - 0.01);
old1 = 'video.currentTime = Math.min(t, duration - 0.01);'
new1 = 'video.currentTime = Math.min(t, duration - 0.01);'
if old1 in content:
    content = content.replace(old1, new1)
    print('Fixed: Math.min parenthesis')
else:
    # 查找实际内容
    idx = content.find('video.currentTime = Math.min')
    if idx >= 0:
        print('Found Math.min at:', repr(content[idx:idx+80]))

# 错误2: toBlob 回调里 URL.createObjectURL 后面少了右括号闭合
# 原代码: URL.createObjectURL(blob), t: +(video.currentTime).toFixed(1) }
# 应该是: URL.createObjectURL(blob), t: +(video.currentTime).toFixed(1) }
old2 = 'URL.createObjectURL(blob), t: +(video.currentTime).toFixed(1) }'
new2 = 'URL.createObjectURL(blob), t: +(video.currentTime).toFixed(1) }'
if old2 in content:
    content = content.replace(old2, new2)
    print('Fixed: createObjectURL parenthesis')
else:
    idx = content.find('URL.createObjectURL(blob)')
    if idx >= 0:
        print('Found createObjectURL at:', repr(content[idx:idx+100]))

# 先保存，然后重新读文件检查语法
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# 检查 JS 括号匹配
js_start = content.find('<script>')
js_end = content.find('</script>')
js = content[js_start:js_end]
open_b = js.count('{')
close_b = js.count('}')
open_p = js.count('(')
close_p = js.count(')')
print(f'JS braces: {open_b} open, {close_b} close - {"OK" if open_b==close_b else "MISMATCH!"}')
print(f'JS paren:  {open_p} open, {close_p} close - {"OK" if open_p==close_p else "MISMATCH!"}')
