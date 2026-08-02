"""极简测试：用 urllib 上传一个小文件，快速触发 tracker"""
import urllib.request, json, time, uuid

vid = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
boundary = uuid.uuid4().hex
with open(vid, 'rb') as f:
    video_data = f.read()

body = b'--' + boundary.encode() + b'\r\nContent-Disposition: form-data; name="video"; filename="test.mp4"\r\nContent-Type: video/mp4\r\n\r\n' + video_data + b'\r\n'
body += b'--' + boundary.encode() + b'\r\nContent-Disposition: form-data; name="duration"\r\n\r\n45\r\n'
body += b'--' + boundary.encode() + b'--\r\n'

req = urllib.request.Request(
    'http://127.0.0.1:8766/api/transcribe',
    data=body,
    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}
)
resp = urllib.request.urlopen(req, timeout=5)
result = json.loads(resp.read())
print('Job:', result.get('job_id'))

jid = result['job_id']
# 只轮询 3 次，每次间隔 0.3 秒
for i in range(4):
    time.sleep(0.3)
    st = urllib.request.urlopen(f'http://127.0.0.1:8766/api/status/{jid}', timeout=3)
    s = json.loads(st.read())
    print(f"[{i+1}] status={s['status']} progress={s.get('progress')} eta={s.get('estimated_remaining')} keys={list(s.keys())}")
    if s['status'] in ('done', 'error', 'no_audio'):
        break
print('完成')
