import subprocess, os, tempfile

ffmpeg = r'C:\Program Files\QClaw\v0.2.31.600\resources\python\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
vid = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
wav = os.path.join(tempfile.gettempdir(), 'test_audio3.wav')

def q(s):
    if ' ' in s or '"' in s:
        return '"' + s.replace('"', '\\"') + '"'
    return s

cmd = '{} -y -i {} -vn -acodec pcm_s16le -ar 16000 -ac 1 -t 5 {}'.format(q(ffmpeg), q(vid), q(wav))
print('FFmpeg:', ffmpeg)
print('Video:', vid)
print('FFmpeg exists:', os.path.exists(ffmpeg))
print('Video exists:', os.path.exists(vid))
print('CMD:', cmd[:200])

r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
print('RC:', r.returncode)
if r.returncode != 0:
    print('STDERR:', r.stderr[:600])
print('WAV exists:', os.path.exists(wav))
if os.path.exists(wav):
    print('WAV size:', os.path.getsize(wav) // 1024, 'KB')
