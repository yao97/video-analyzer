import urllib.request, json, time, os

video_path = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
url = 'http://127.0.0.1:8766/api/transcribe'

# 读文件，手动拼 multipart
with open(video_path, 'rb') as f:
    filedata = f.read()

boundary = '----FormBoundary7b4a'
payload = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="video"; filename="test.mp4"\r\n'
    f'Content-Type: video/mp4\r\n\r\n'
).encode() + filedata + (
    f'\r\n--{boundary}\r\n'
    f'Content-Disposition: form-data; name="duration"\r\n\r\n'
    f'45\r\n'
    f'--{boundary}--\r\n'
).encode()

req = urllib.request.Request(
    url,
    data=payload,
    headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Content-Length': str(len(payload)),
    }
)
try:
    resp = urllib.request.urlopen(req, timeout=15)
    job = json.loads(resp.read())
    print('Job created:', job)
    job_id = job['job_id']
except Exception as e:
    print('Upload failed:', e)
    import traceback; traceback.print_exc()
    raise

# 轮询
for i in range(20):
    time.sleep(1)
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:8766/api/status/{job_id}', timeout=5)
        s = json.loads(r.read())
        print(f'[{i+1}s] status={s["status"]} progress={s["progress"]}%')
        if s['status'] in ('done', 'error', 'no_audio'):
            r2 = urllib.request.urlopen(f'http://127.0.0.1:8766/api/result/{job_id}', timeout=5)
            res = json.loads(r2.read())
            print('Result:', json.dumps(res, ensure_ascii=False)[:400])
            break
    except Exception as e:
        print(f'[{i+1}s] Error: {e}')
        break
