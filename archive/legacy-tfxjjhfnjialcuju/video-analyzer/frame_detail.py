"""Deep frame analysis for copywriting breakdown."""
import sys, os, cv2, numpy as np
sys.path.insert(0, r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\src')

video_path = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
frame_dir = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\frames'

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()

times = [0, 2, 5, 10, 15, 20, 25, 30, 35, 40]
frames = {}
for t in times:
    p = os.path.join(frame_dir, f'frame_{t:04.0f}s.jpg')
    if os.path.exists(p):
        frames[t] = cv2.imread(p)

def analyze_frame_detail(frame, t):
    h, w = frame.shape[:2]
    top = frame[0:h//3, :]
    mid = frame[h//3:2*h//3, :]
    bot = frame[2*h//3:h, :]
    cy, cx = h//2, w//2
    center = frame[cy-100:cy+100, cx-50:cx+50]

    def region_colors(r):
        return (round(r[:,:,2].mean(),1), round(r[:,:,1].mean(),1), round(r[:,:,0].mean(),1))

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hue = hsv[:,:,0].mean()
    sat = hsv[:,:,1].mean()
    val = hsv[:,:,2].mean()
    red_mask = ((hsv[:,:,0] < 15) | (hsv[:,:,0] > 170)) & (hsv[:,:,1] > 80)
    red_ratio = red_mask.mean()
    white_mask = (hsv[:,:,2] > 220) & (hsv[:,:,1] < 40)
    white_ratio = white_mask.mean()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = edges.mean() / 255
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    large_contours = [c for c in contours if cv2.contourArea(c) > 500]
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    text_pixels = binary.sum() / 255
    has_text = text_pixels > 5000
    bright_top = region_colors(top)[0]*0.299 + region_colors(top)[1]*0.587 + region_colors(top)[2]*0.114
    tone = 'WARM_RED' if red_ratio > 0.15 else ('HIGH_WHITE' if white_ratio > 0.2 else 'NEUTRAL')
    top_rgb = region_colors(top)
    mid_rgb = region_colors(mid)
    bot_rgb = region_colors(bot)
    return {
        't': t, 'hue': round(hue,1), 'sat': round(sat,1), 'val': round(val,1),
        'red_ratio': round(red_ratio,3), 'white_ratio': round(white_ratio,3),
        'edge_density': round(edge_density,3), 'large_contours': len(large_contours),
        'has_text': has_text, 'brightness': round(bright_top/255,2), 'tone': tone,
        'top_rgb': top_rgb, 'mid_rgb': mid_rgb, 'bot_rgb': bot_rgb
    }

print('=' * 80)
print('FRAME ANALYSIS FOR COPYWRITING BREAKDOWN')
print('=' * 80)
print()
print('Frame |  Hue  |  Sat  |  Val  | Red%  | Wht%  | Edge  | Contours | Text | Bright | Tone')
print('-' * 80)
for t in sorted(frames.keys()):
    r = analyze_frame_detail(frames[t], t)
    tt = str(r['has_text'])
    print('%5ds | %5.1f | %5.1f | %5.1f | %5.1f%% | %5.1f%% | %.3f  | %9d | %5s | %.2f | %s' % (
        r['t'], r['hue'], r['sat'], r['val'],
        r['red_ratio']*100, r['white_ratio']*100,
        r['edge_density'], r['large_contours'], tt, r['brightness'], r['tone']
    ))

print()
print('=' * 80)
print('COPYWRITING STRUCTURE ANALYSIS')
print('=' * 80)
