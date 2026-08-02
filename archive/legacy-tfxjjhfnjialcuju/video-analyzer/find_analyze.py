import re

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Find analyzeFrames function
idx = content.find('function analyzeFrames')
if idx > 0:
    # Get the function
    end = content.find('\nfunction ', idx + 100)
    if end == -1:
        end = idx + 5000
    func = content[idx:end]
    
    # Find where contentType is set in the return value
    if 'contentType' in func:
        # Find the return statement
        ret_idx = func.find('return {')
        if ret_idx > 0:
            print('analyzeFrames return statement:')
            print(func[ret_idx:ret_idx+500])
    else:
        print('contentType not found in analyzeFrames')
        print('Function snippet:')
        print(func[:1000])
else:
    print('analyzeFrames not found')
