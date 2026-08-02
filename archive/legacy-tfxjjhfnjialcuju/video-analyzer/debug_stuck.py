"""Debug what's happening with the stuck transcription job."""
import urllib.request, json, time, sys

job_id = "d9b6e060"

for i in range(3):
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:8766/api/status/{job_id}', timeout=5)
        data = json.loads(r.read().decode())
        print(f"[{i}] {data['status']} | progress={data['progress']} | chunk={data.get('current_chunk','?')} | error={data.get('error','?')}")
    except Exception as e:
        print(f"[{i}] Failed: {e}")
    time.sleep(2)
