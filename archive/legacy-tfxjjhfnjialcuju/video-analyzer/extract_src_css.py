import re
src = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(src, encoding='utf-8') as f:
    html = f.read()
m = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
if m:
    css = m.group(1)
    print(f'Source CSS length: {len(css)}')
    with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\extracted_css.txt', 'w', encoding='utf-8') as f:
        f.write(css)
    print('CSS extracted from source')
    # Show first 100 chars
    print(repr(css[:100]))
else:
    print('No CSS found in source')
