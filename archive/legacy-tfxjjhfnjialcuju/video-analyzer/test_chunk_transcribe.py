"""测试分片转写 + 实时进度监控"""
import urllib.request, json, time, os

VIDEO = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
BOUNDARY = '----WebKitFormBoundary7MA4YWxkTrZu0gW'

with open(VIDEO, 'rb') as f:
    video_data = f.read()

print(f"视频大小: {len(video_data)/1024/1024:.2f} MB")

# 构造 multipart/form-data
fields = (b'--' + BOUNDARY.encode() + b'\r\n'
          b'Content-Disposition: form-data; name="duration"\r\n\r\n45\r\n')
video_part = (b'--' + BOUNDARY.encode() + b'\r\n'
             b'Content-Disposition: form-data; name="video"; filename="test.mp4"\r\n'
             b'Content-Type: video/mp4\r\n\r\n')
footer = b'\r\n--' + BOUNDARY.encode() + b'--\r\n'
body = fields + video_part + video_data + footer

req = urllib.request.Request(
    'http://127.0.0.1:8766/api/transcribe',
    data=body,
    headers={'Content-Type': 'multipart/form-data; boundary=' + BOUNDARY}
)

print("上传视频...")
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print(f"任务创建: {result}")
    job_id = result['job_id']
except Exception as e:
    print(f"上传失败: {e}")
    raise SystemExit

# 轮询进度
print(f"\n开始监控 job_id={job_id}...\n")
last_progress = -1
for i in range(60):
    time.sleep(1)
    try:
        r2 = urllib.request.urlopen(f'http://127.0.0.1:8766/api/status/{job_id}', timeout=5)
        s = json.loads(r2.read())
        prog = s['progress']
        status = s['status']
        chunk = s.get('current_chunk', '')

        # 只在进度变化或状态变化时打印
        if prog != last_progress or status != 'transcribing':
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [{i+1}s] status={status} progress={prog}% {chunk}")
            last_progress = prog

        if status in ('done', 'error', 'no_audio'):
            print(f"\n=== 任务结束: {status} ===")
            if status == 'done':
                r3 = urllib.request.urlopen(f'http://127.0.0.1:8766/api/result/{job_id}', timeout=10)
                res = json.loads(r3.read())
                text = res['result']['text']
                segs = res['result']['segments']
                print(f"转写文本 ({len(text)} 字, {len(segs)} 段):")
                print(text[:200] + ('...' if len(text) > 200 else ''))
            elif status == 'error':
                print(f"错误: {s.get('error')}")
            break
    except urllib.error.HTTPError as e:
        print(f"[{i+1}s] HTTP 错误: {e.code}")
        if e.code == 404:
            break
    except Exception as e:
        print(f"[{i+1}s] 错误: {e}")
else:
    print("超时（60秒）")
