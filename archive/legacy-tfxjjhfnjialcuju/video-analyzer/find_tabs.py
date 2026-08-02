f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'r', encoding='utf-8')
c = f.read()
f.close()
lines = c.split('\n')
for i, l in enumerate(lines):
    if 'id="tab' in l or 'id="contentArea' in l:
        print(i+1, repr(l[:100]))
