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
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())
print('Job ID:', result.get('job_id'))

jid = result['job_id']
for i in range(8):
    time.sleep(1)
    try:
        st = urllib.request.urlopen(f'http://127.0.0.1:8766/api/status/{jid}', timeout=5)
        s = json.loads(st.read())
        # 打印原始 JSON
        print(f"[{i+1}] RAW: {json.dumps(s, ensure_ascii=False)}")
        if s['status'] == 'done':
            print('Done!')
            break
        if s['status'] == 'error':
            print('Error:', s.get('error'))
            break
    except Exception as e:
        print(f"[{i+1}] Error: {e}")
