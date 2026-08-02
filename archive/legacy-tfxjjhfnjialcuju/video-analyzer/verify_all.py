with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

result = []
# Check tab button
if '拍摄手法' in content:
    result.append('[OK] Tab button added')
else:
    result.append('[FAIL] Tab button missing')

# Check tab panel
if 'tabShooting' in content:
    result.append('[OK] Tab panel added')
else:
    result.append('[FAIL] Tab panel missing')

# Check renderShooting function
if 'function renderShooting' in content:
    result.append('[OK] renderShooting function added')
else:
    result.append('[FAIL] renderShooting function missing')

# Check renderShooting call
if 'renderShooting(analysisResult)' in content:
    result.append('[OK] renderShooting call added')
else:
    result.append('[FAIL] renderShooting call missing')

# Check transcribe_server.py model
with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', encoding='utf-8') as f:
    server_content = f.read()
if 'load_model("small"' in server_content:
    result.append('[OK] Whisper model set to small')
elif 'load_model("tiny")' in server_content:
    result.append('[FAIL] Whisper model still tiny')
else:
    result.append('[WARN] Cannot determine Whisper model')

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\verify_all_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(result))

print('Verification done, see verify_all_output.txt')
