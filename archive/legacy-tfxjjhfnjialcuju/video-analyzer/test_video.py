"""Quick video analysis test script."""
import sys, os, time
sys.path.insert(0, r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\src')

video_path = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
print(f'File: {os.path.basename(video_path)}')
print(f'Size: {os.path.getsize(video_path) / 1024 / 1024:.2f} MB')

import cv2
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
duration = frame_count / fps if fps > 0 else 0
cap.release()

print(f'Duration: {duration:.2f}s | FPS: {fps:.2f} | Resolution: {width}x{height} | Frames: {frame_count}')

# Extract frames
cap = cv2.VideoCapture(video_path)
sample_count = 6
sample_indices = [int(i * frame_count / sample_count) for i in range(sample_count)]
frames = {}
for idx in sample_indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if ret:
        frames[idx] = frame
cap.release()

def analyze_frame(frame):
    h, w = frame.shape[:2]
    cy, cx = h // 2, w // 2
    crop = frame[cy - 50:cy + 50, cx - 50:cx + 50]
    b_mean = crop[:, :, 0].mean()
    g_mean = crop[:, :, 1].mean()
    r_mean = crop[:, :, 2].mean()
    brightness = (r_mean * 0.299 + g_mean * 0.587 + b_mean * 0.114) / 255
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0].mean()
    if hue < 15 or hue > 165:
        tone = '红/暖'
    elif hue < 40:
        tone = '黄'
    elif hue < 70:
        tone = '绿'
    elif hue < 140:
        tone = '青/蓝绿'
    elif hue < 170:
        tone = '蓝'
    else:
        tone = '紫/粉'
    return {
        'rgb': (round(r_mean, 1), round(g_mean, 1), round(b_mean, 1)),
        'brightness': round(brightness, 2),
        'tone': tone
    }

print('\n=== 帧画面分析 ===')
for idx in sorted(frames.keys()):
    frame = frames[idx]
    ts = idx / fps
    c = analyze_frame(frame)
    shape = frame.shape
    print(f'  [{idx:04d}] t={ts:5.1f}s | {shape[1]}x{shape[0]} | RGB{c["rgb"]} | 亮度={c["brightness"]} | 色调={c["tone"]}')

print('\nResult: SUCCESS')
