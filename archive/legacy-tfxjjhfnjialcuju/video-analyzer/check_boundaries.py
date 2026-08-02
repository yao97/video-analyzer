lines = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html', encoding='utf-8').readlines()
# GET_PHASE_FN = block(1002, 1065) = lines[1001:1065] = L1002-L1065
gp = ''.join(lines[1001:1065])
print('GET_PHASE_FN last 5 lines:')
for i, l in enumerate(gp.split('\n')[-5:]):
    print(f'  L{len(gp.split(chr(10)))-5+i+1}: {repr(l[:70])}')
print()
# CT_META = block(1066, 1093) = lines[1065:1093] = L1066-L1093
ct = ''.join(lines[1065:1093])
print('CT_META first 5 lines:')
for i, l in enumerate(ct.split('\n')[:5]):
    print(f'  L{1066+i}: {repr(l[:70])}')
print('CT_META last 3 lines:')
for i, l in enumerate(ct.split('\n')[-3:]):
    print(f'  L{1091+i}: {repr(l[:70])}')
print()
# PROCESS_FN = block(1093, 1246) = lines[1092:1246] = L1093-L1246
pf = ''.join(lines[1092:1246])
print('PROCESS_FN first 2 lines:')
for i, l in enumerate(pf.split('\n')[:2]):
    print(f'  L{1093+i}: {repr(l[:70])}')
