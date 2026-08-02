"""直接测试：上传一个有声音的视频到转写服务，看完整流程"""
import urllib.request, json, time, os

VIDEO = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
url = 'http://127.0.0.1:8766/api/transcribe'

# 读文件上传
with open(VIDEO, 'rb') as f:
    data = f.read()

boundary = '----FormBoundary7b4a0001'
payload = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="video"; filename="test.mp4"\r\n'
    f'Content-Type: video/mp4\r\n\r\n'
).encode() + data + (
    f'\r\n--{boundary}\r\n'
    f'Content-Disposition: form-data; name="duration"\r\n\r\n'
    f'45\r\n'
    f'--{boundary}--\r\n'
).encode()

req = urllib.request.Request(url, data=payload, headers={
    'Content-Type': f'multipart/form-data; boundary={boundary}',
    'Content-Length': str(len(payload)),
})
resp = urllib.request.urlopen(req, timeout=15)
job = json.loads(resp.read())
job_id = job['job_id']
print(f'任务创建: {job_id}')
print(f'状态: {job["status"]}')
print(f'消息: {job["message"]}')

# 轮询结果
for i in range(30):
    time.sleep(1)
    r = urllib.request.urlopen(f'http://127.0.0.1:8766/api/status/{job_id}', timeout=5)
    s = json.loads(r.read())
    status = s['status']
    progress = s.get('progress', 0)
    current = s.get('current_chunk', '')
    
    if status == 'transcribing':
        print(f'[{i+1}s] 转写中 {progress:.0f}%  {current}')
    elif status == 'extracting':
        print(f'[{i+1}s] 提取音频中...')
    elif status == 'no_audio':
        print(f'[{i+1}s] 无音轨')
        break
    elif status == 'done':
        print(f'[{i+1}s] 完成！')
        r2 = urllib.request.urlopen(f'http://127.0.0.1:8766/api/result/{job_id}', timeout=5)
        res = json.loads(r2.read())
        result = res.get('result', {})
        print(f'文本: {result.get("text", "")[:100]}')
        print(f'关键词: {result.get("keywords", {})}')
        break
    elif status == 'error':
        print(f'[{i+1}s] 错误: {s.get("error")}')
        break
    else:
        print(f'[{i+1}s] {status} {progress}%')
