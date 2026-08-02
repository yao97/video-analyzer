import re
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    html = f.read()
m = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
if m:
    css = m.group(1)
    print(f'CSS length: {len(css)}')
    with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\extracted_css.txt', 'w', encoding='utf-8') as f:
        f.write(css)
    print('CSS extracted')
else:
    print('No CSS found')
