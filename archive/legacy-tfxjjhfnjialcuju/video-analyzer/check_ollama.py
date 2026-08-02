# -*- coding: utf-8 -*-
import io, re, subprocess, os
path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
c = io.open(path, encoding='utf-8').read()

# extract script blocks
scripts = re.findall(r'<script>(.*?)</script>', c, re.S)
print('script blocks:', len(scripts))
js = max(scripts, key=len)
open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\_check.js', 'w', encoding='utf-8').write(js)

# syntax check via node
node = r'C:\Program Files\nodejs\node.exe'
if os.path.exists(node):
    r = subprocess.run([node, '--check', r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\_check.js'],
                       capture_output=True, text=True)
    print('node --check rc:', r.returncode)
    if r.returncode != 0:
        print(r.stderr[:1500])
else:
    print('node not found')

# presence checks
for needle in ['onProviderChange', 'testOllama', 'name="deepProvider"', 'deepOllamaBlock',
               'deepOllamaBase', "provider: 'ollama'", 'ollama_base: ollamaBase',
               'provider: provider', "JSON.stringify({provider: 'ollama'"]:
    print(('OK ' if needle in c else 'MISSING ') + needle)
# count duplicate functions
for fn in ['function onProviderChange', 'function testOllama', 'function testApiKey',
           'function doDeepAnalysis', 'function deepGoStep1']:
    print(fn, '->', c.count(fn))
