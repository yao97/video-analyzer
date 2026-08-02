with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Find exact location of renderReport call
import re

# Pattern: renderReport(analysisResult, speechResult);
pattern = r'renderReport\(analysisResult,\s*speechResult\);'
match = re.search(pattern, content)
if match:
    idx = match.end()
    # Insert renderShooting call after it
    new_code = 'renderReport(analysisResult, speechResult);\n    renderShooting(analysisResult);'
    content = content[:match.start()] + new_code + content[match.end():]
    print('[OK] Inserted renderShooting call')
else:
    print('[FAIL] renderReport call not found')
    # Search for any renderReport
    idx2 = content.find('renderReport')
    if idx2 > 0:
        print('Found renderReport at:', idx2)
        print('Context:', content[idx2:idx2+100])

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
