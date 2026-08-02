import urllib.request, json

# Test transcribe server
try:
    r = urllib.request.urlopen('http://127.0.0.1:8766/', timeout=5)
    print("Transcribe server (8766): OK", r.read(50))
except Exception as e:
    print("Transcribe server (8766): FAIL", e)

# Test page server
try:
    r = urllib.request.urlopen('http://127.0.0.1:8765/', timeout=5)
    content = r.read(200)
    print("Page server (8765): OK, first 100 bytes:", content[:100])
except Exception as e:
    print("Page server (8765): FAIL", e)
