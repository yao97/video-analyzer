"""Ultrasound scalpel (ultrasonic skin treatment) video - proper re-analysis."""
import sys, os, cv2, numpy as np
sys.path.insert(0, r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\src')

video_path = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'
frame_dir = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\frames'

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
duration = total / fps
cap.release()

print('Video: %.1fs, %dx%d, %.1ffps' % (duration, width, height, fps))

# Extract frames every 5s
times = list(range(0, int(duration), 5))
os.makedirs(frame_dir, exist_ok=True)
cap = cv2.VideoCapture(video_path)
saved = []
for t in times:
    idx = int(t * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if ret:
        small = cv2.resize(frame, (360, int(360 * height / width)))
        out = os.path.join(frame_dir, 'u_%ds.jpg' % t)
        cv2.imwrite(out, small)
        saved.append((t, out))
cap.release()

# ---- Deep analysis with ultrasound context ----
def analyze_ultrasound_frame(frame, t):
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Skin tone detection (important for ultrasound treatment)
    # Skin hue range: H=0-20 (red/yellow) + slightly into orange
    # Normal skin: low sat, mid val
    skin_mask = ((hsv[:,:,0] < 20) | ((hsv[:,:,0] > 0) & (hsv[:,:,0] < 25))) & \
                (hsv[:,:,1] > 20) & (hsv[:,:,1] < 120) & \
                (hsv[:,:,2] > 60) & (hsv[:,:,2] < 230)
    skin_ratio = round(skin_mask.mean(), 3)

    # Redness/erythema (ultrasound treatment causes skin redness)
    # H=0-10 or H=170-180, high saturation
    redness_mask = ((hsv[:,:,0] < 10) | (hsv[:,:,0] > 170)) & (hsv[:,:,1] > 80) & (hsv[:,:,2] > 60)
    redness_ratio = round(redness_mask.mean(), 3)

    # Pink/red blush (ultrasound post-treatment or active treatment)
    blush_mask = ((hsv[:,:,0] >= 0) & (hsv[:,:,0] < 20)) & (hsv[:,:,1] > 60) & (hsv[:,:,1] < 150)
    blush_ratio = round(blush_mask.mean(), 3)

    # White/pure white (device screen, clinic environment)
    white_mask = (hsv[:,:,2] > 230) & (hsv[:,:,1] < 30)
    white_ratio = round(white_mask.mean(), 3)

    # Blue/teal (medical device UI, ultrasound screen)
    blue_mask = (hsv[:,:,0] >= 90) & (hsv[:,:,0] <= 130) & (hsv[:,:,1] > 40)
    blue_ratio = round(blue_mask.mean(), 3)

    # Green (OK/confirm buttons, medical indicators)
    green_mask = (hsv[:,:,0] >= 35) & (hsv[:,:,0] < 75) & (hsv[:,:,1] > 60)
    green_ratio = round(green_mask.mean(), 3)

    # Dark regions (text areas, device interface)
    dark_mask = hsv[:,:,2] < 50
    dark_ratio = round(dark_mask.mean(), 3)

    # Text detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    text_pixels = binary.sum() / 255
    text_ratio = round(text_pixels / (h*w) * 100, 2)
    has_text = text_pixels > 2000

    # UI element detection (rectangles, panels)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rects = 0
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        if len(approx) == 4 and cv2.contourArea(c) > 500:
            rects += 1

    # Screen/device region (bright rectangular areas)
    _, bright_binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours2, _ = cv2.findContours(bright_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bright_rects = sum(1 for c in contours2 if 1000 < cv2.contourArea(c) < h*w*0.8)

    # Average brightness and color per region
    def region_stats(r):
        return {'rgb': (round(r[:,:,2].mean(),1), round(r[:,:,1].mean(),1), round(r[:,:,0].mean(),1)),
                'bright': round((r[:,:,2].mean()*0.299 + r[:,:,1].mean()*0.587 + r[:,:,0].mean()*0.114)/255, 2)}

    # Split vertical frame into 3 parts (typical ultrasound UI layout)
    top = frame[0:h//3, :]
    mid = frame[h//3:2*h//3, :]
    bot = frame[2*h//3:h, :]

    top_s = region_stats(top)
    mid_s = region_stats(mid)
    bot_s = region_stats(bot)

    # Center crop analysis
    cy, cx = h//2, w//2
    center = frame[cy-80:cy+80, cx-40:cx+40]
    center_s = region_stats(center)

    # Motion detection (treating/moving probe)
    # We'll note brightness in center as proxy for active treatment area
    active_area = center_s['bright']

    # Face/skin area detection (likely present in treatment video)
    # Skin-like pixels in middle region
    mid_hsv = cv2.cvtColor(mid, cv2.COLOR_BGR2HSV)
    mid_skin = ((mid_hsv[:,:,0] < 25) | (mid_hsv[:,:,0] > 0)) & \
               (mid_hsv[:,:,1] > 20) & (mid_hsv[:,:,1] < 120) & \
               (mid_hsv[:,:,2] > 60) & (mid_hsv[:,:,2] < 230)
    skin_in_mid = round(mid_skin.mean(), 3)

    return {
        't': t,
        'skin_ratio': skin_ratio,
        'redness_ratio': redness_ratio,
        'blush_ratio': blush_ratio,
        'white_ratio': white_ratio,
        'blue_ratio': blue_ratio,
        'green_ratio': green_ratio,
        'dark_ratio': dark_ratio,
        'text_ratio': text_ratio,
        'has_text': has_text,
        'rects': rects,
        'bright_rects': bright_rects,
        'top_rgb': top_s['rgb'],
        'mid_rgb': mid_s['rgb'],
        'bot_rgb': bot_s['rgb'],
        'center_rgb': center_s['rgb'],
        'center_bright': center_s['bright'],
        'skin_in_mid': skin_in_mid
    }

print()
print('=' * 75)
print('  ULTRASOUND SCALPEL VIDEO - STRUCTURED ANALYSIS')
print('=' * 75)
print()
print('File: 7080470245349068032.mp4 | 超声炮视频')
print()

all_results = []
for t, path in saved:
    frame = cv2.imread(path)
    if frame is None:
        continue
    r = analyze_ultrasound_frame(frame, t)
    all_results.append(r)

# Print main metrics table
print('[MEDICAL COLOR ANALYSIS - 每帧颜色分布]')
print('%-6s | %-6s | %-6s | %-6s | %-6s | %-6s | %-6s | %-6s | %-6s | Text' % (
    'Time', 'Skin%', 'Redness%', 'Blush%', 'White%', 'Blue%', 'Green%', 'Dark%', 'Skin/M'))
print('-' * 80)
for r in all_results:
    print('%-6ds | %5.1f%% | %5.1f%% | %5.1f%% | %5.1f%% | %5.1f%% | %5.1f%% | %5.1f%% | %5.1f%% | %s' % (
        r['t'], r['skin_ratio']*100, r['redness_ratio']*100, r['blush_ratio']*100,
        r['white_ratio']*100, r['blue_ratio']*100, r['green_ratio']*100,
        r['dark_ratio']*100, r['skin_in_mid']*100, str(r['has_text'])
    ))

print()
print('[UI/TEXT DENSITY]')
print('%-6s | %-6s | %-6s | %-6s | %-10s | Brightness (Top/Mid/Center)' % (
    'Time', 'Text%', 'Rects', 'BrightRects', 'Center Bright'))
print('-' * 75)
for r in all_results:
    print('%-6ds | %5.2f%% | %6d | %9d | %10.2f | T=%s M=%s C=%s' % (
        r['t'], r['text_ratio'], r['rects'], r['bright_rects'],
        r['center_bright'], r['top_rgb'], r['mid_rgb'], r['center_rgb']
    ))

print()
print('=' * 75)
print('  CONTENT STRUCTURE BREAKDOWN')
print('=' * 75)

# Determine content phases
for r in all_results:
    phase = ''
    if r['skin_ratio'] > 0.15 and r['skin_in_mid'] > 0.1:
        content = 'SKIN/FACE (治疗画面)'
    elif r['blue_ratio'] > 0.03:
        content = 'DEVICE UI / 设备界面'
    elif r['white_ratio'] > 0.3:
        content = 'CLINIC ENVIRONMENT (诊所环境)'
    elif r['redness_ratio'] > 0.05:
        content = 'TREATMENT ACTIVE (治疗中/红肿)'
    elif r['text_ratio'] > 0.5:
        content = 'TEXT OVERLAY / 字幕说明'
    else:
        content = 'TRANSITION / 转场'
    print('  @%ds: %s (skin=%.1f%%, red=%.1f%%, blue=%.1f%%, white=%.1f%%, text=%.1f%%)' % (
        r['t'], content, r['skin_ratio']*100, r['redness_ratio']*100,
        r['blue_ratio']*100, r['white_ratio']*100, r['text_ratio']
    ))

print()
print('=' * 75)
print('  KEY INSIGHTS')
print('=' * 75)

# Aggregate analysis
avg_skin = sum(r['skin_ratio'] for r in all_results) / len(all_results)
avg_redness = sum(r['redness_ratio'] for r in all_results) / len(all_results)
avg_blush = sum(r['blush_ratio'] for r in all_results) / len(all_results)
avg_white = sum(r['white_ratio'] for r in all_results) / len(all_results)
avg_blue = sum(r['blue_ratio'] for r in all_results) / len(all_results)
avg_text = sum(r['text_ratio'] for r in all_results) / len(all_results)
avg_skin_mid = sum(r['skin_in_mid'] for r in all_results) / len(all_results)

has_device_ui = any(r['blue_ratio'] > 0.01 for r in all_results)
has_skin = avg_skin_mid > 0.05
has_text = any(r['has_text'] for r in all_results)

print()
print('  [COLOR SIGNATURE SUMMARY]')
print('  Skin tones avg:  %.1f%%  (脸部/皮肤出现频率)' % (avg_skin*100))
print('  Redness avg:      %.1f%%  (治疗红肿/设备指示)' % (avg_redness*100))
print('  Blush/pink avg:   %.1f%%  (治疗后泛红)' % (avg_blush*100))
print('  White/clinic avg: %.1f%%  (诊所/设备/背景)' % (avg_white*100))
print('  Blue/device UI:   %.1f%%  (医疗设备界面/按钮)' % (avg_blue*100))
print('  Text overlay:     %.1f%%  (字幕/说明文字)' % avg_text)
print()
print('  Device UI present:   %s' % ('YES' if has_device_ui else 'NO'))
print('  Skin/face content:   %s' % ('YES' if has_skin else 'NO'))
print('  Text overlays:       %s' % ('YES' if has_text else 'NO'))

# Find max redness frames
max_red = max(all_results, key=lambda r: r['redness_ratio'])
max_white = max(all_results, key=lambda r: r['white_ratio'])
max_blue = max(all_results, key=lambda r: r['blue_ratio'])
max_text = max(all_results, key=lambda r: r['text_ratio'])

print()
print('  [PEAK FRAMES]')
print('  Most redness:    @%ds (%.1f%%)' % (max_red['t'], max_red['redness_ratio']*100))
print('  Most white:      @%ds (%.1f%%)' % (max_white['t'], max_white['white_ratio']*100))
print('  Most device blue:@%ds (%.1f%%)' % (max_blue['t'], max_blue['blue_ratio']*100))
print('  Most text:       @%ds (%.1f%%)' % (max_text['t'], max_text['text_ratio']))

print()
print('=' * 75)
