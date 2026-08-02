path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Find chart.js line
idx = content.find('chart.js@4.4.0')
if idx > 0:
    context = content[idx-20:idx+200]
    print('Context around chart.js:')
    print(repr(context))
    
    # Check for escaped script tag
    if '<\\/' in context:
        print('\n*** FOUND ESCAPED TAG: <\\/script> ***')
    elif '</script>' in context:
        print('\n*** FOUND NORMAL TAG: </script> ***')
