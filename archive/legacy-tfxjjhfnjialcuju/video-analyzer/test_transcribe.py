"""测试转写进度追踪"""
import urllib.request, urllib.error, json, time

video = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'

with open(video, 'rb') as f:
    video_data = f.read()

fields = b'--' + boundary.encode() + b'\r\nContent-Disposition: form-data; name="duration"\r\n\r\n45\r\n'
video_part = b'--' + boundary.encode() + b'\r\nContent-Disposition: form-data; name="video"; filename="test.mp4"\r\nContent-Type: video/mp4\r\n\r\n' + video_data + b'\r\n'
footer = b'--' + boundary.encode() + b'--\r\n'
body = fields + video_part + footer

req = urllib.request.Request(
    'http://127.0.0.1:8766/api/transcribe',
    data=body,
    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}
)

try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print('Upload result:', result)
    job_id = result['job_id']

    for i in range(20):
        time.sleep(1)
        try:
            r2 = urllib.request.urlopen(f'http://127.0.0.1:8766/api/status/{job_id}', timeout=5)
            s = json.loads(r2.read())
            print(f"[{i+1}] status={s['status']} progress={s['progress']} eta={s.get('estimated_remaining')}")
            if s['status'] in ('done', 'error', 'no_audio', 'analyzing'):
                print('Final!')
                break
        except urllib.error.URLError as ex:
            print(f'[{i+1}] URL error: {ex}')
        except Exception as ex:
            print(f'[{i+1}] error: {ex}')
except Exception as e:
    print('Upload error:', e)
