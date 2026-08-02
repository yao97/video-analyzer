import urllib.request, json, sys

try:
    r = urllib.request.urlopen('http://127.0.0.1:8766/api/status/d9b6e060', timeout=5)
    data = json.loads(r.read().decode())
    print("Job status:", json.dumps(data, ensure_ascii=False, indent=2))
except Exception as e:
    print("Failed:", e)
    sys.exit(1)
