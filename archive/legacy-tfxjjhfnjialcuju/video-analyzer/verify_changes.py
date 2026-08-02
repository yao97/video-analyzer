f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'r', encoding='utf-8')
c = f.read()
f.close()
lines = c.split('\n')
print(f'Total lines: {len(lines)}')
print(f'Total chars: {len(c)}')
print()

print('=== New tab buttons ===')
for i, l in enumerate(lines):
    if 'tab active' in l or "switchTab(this" in l:
        if 'class="tab' in l:
            print(f'[{i+1}] {repr(l.strip()[:100])}')

print()
print('=== Tab content divs ===')
for i, l in enumerate(lines):
    if 'id="tab' in l:
        print(f'[{i+1}] {repr(l.strip()[:100])}')

print()
print('=== New JS functions ===')
for i, l in enumerate(lines):
    if 'function doDeep' in l or 'function showDeep' in l or 'function renderDeep' in l or 'function setDeep' in l or 'function downloadDeep' in l:
        print(f'[{i+1}] {repr(l.strip()[:80])}')

print()
print('=== Key elements exist ===')
print('tabDeepReport:', 'id="tabDeepReport"' in c)
print('btnDeepAnalyze:', 'id="btnDeepAnalyze"' in c)
print('deepReportMarkdown:', 'id="deepReportMarkdown"' in c)
print('deepReportContent:', 'id="deepReportContent"' in c)
print('doDeepAnalysis:', 'function doDeepAnalysis' in c)
print('renderDeepReport:', 'function renderDeepReport' in c)
print('TRANSCRIBE_BASE:', 'TRANSCRIBE_BASE' in c)
