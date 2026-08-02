import urllib.request, json, time

# 上传视频文件
url = 'http://127.0.0.1:8766/api/transcribe'
video_path = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'

with open(video_path, 'rb') as f:
    files = {'video': ('test.mp4', f, 'video/mp4')}
    data = urllib.request.urlencode({'duration': '45'}).encode()
    # 用 MultipartEncoder 发送文件
    import requests
    r = requests.post(url, files={'video': ('test.mp4', open(video_path,'rb'), 'video/mp4')}, data={'duration': 45})
    print('Upload response:', r.json())
