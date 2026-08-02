"""Test: upload a video to the transcribe server and check the result.
   Use the ultrasound video (no audio) first to verify no_audio status works,
   then generate a simple test video with audio.
"""
import urllib.request, json, time, os, subprocess, tempfile

# ── Step 1: Test with no-audio video ──
video_path = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
url = 'http://127.0.0.1:8766/api/transcribe'

# Read file and upload
with open(video_path, 'rb') as f:
    filedata = f.read()

boundary = '----FormBoundary7b4a0001'
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

# Poll for result (should be fast since no audio)
for i in range(10):
    time.sleep(1)
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:8766/api/status/{job_id}', timeout=5)
        s = json.loads(r.read())
        print(f'[{i+1}s] status={s["status"]} progress={s["progress"]}%')
        if s['status'] in ('done', 'error', 'no_audio'):
            r2 = urllib.request.urlopen(f'http://127.0.0.1:8766/api/result/{job_id}', timeout=5)
            res = json.loads(r2.read())
            print('Result status:', res.get('status'))
            print('Result has result?', 'result' in res)
            if 'result' in res:
                r = res['result']
                print('  no_audio:', r.get('no_audio'))
                print('  error:', r.get('error'))
            break
    except Exception as e:
        print(f'[{i+1}s] Error: {e}')
        break

print('\nDone with no-audio test.')
