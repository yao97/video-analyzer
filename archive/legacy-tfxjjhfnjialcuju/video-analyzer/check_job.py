import urllib.request, json, time

job_id = 'cb66c915'
for i in range(20):
    time.sleep(3)
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:8766/api/status/{job_id}', timeout=5)
        s = json.loads(r.read())
        status = s['status']
        progress = s['progress']
        chunk = s.get('current_chunk', '')
        print(f'[{i*3}s] status={status} progress={progress}% {chunk}')
        if status in ('done', 'error', 'no_audio'):
            # 获取结果
            r2 = urllib.request.urlopen(f'http://127.0.0.1:8766/api/result/{job_id}', timeout=10)
            res = json.loads(r2.read())
            print('Result:', json.dumps(res, ensure_ascii=False, indent=2)[:500])
            break
    except Exception as e:
        print(f'[{i*3}s] Error: {e}')
        break
