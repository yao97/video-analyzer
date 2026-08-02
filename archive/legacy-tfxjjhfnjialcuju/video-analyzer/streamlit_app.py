"""
Video Content Analyzer - Web Preview Page
视频内容分析系统 - Web 预览页面
支持上传视频 → 分帧拆解 → 内容分析 → 文案结构提取
"""
from __future__ import annotations

import os
import sys
import time
import tempfile
import hashlib
import io
from pathlib import Path
from datetime import datetime
from typing import Optional

import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Page Config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Video Content Analyzer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', 'Microsoft YaHei', sans-serif; }

    .stApp { background: #0f1117; }

    /* Header */
    .main-header {
        font-size: 2rem; font-weight: 700; color: #ffffff;
        padding: 1rem 0 0.5rem 0; letter-spacing: -0.5px;
    }
    .sub-header {
        font-size: 0.95rem; color: #8b8fa3; margin-bottom: 2rem;
        font-weight: 400;
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1d27 0%, #232636 100%);
        border: 1px solid #2a2d3a;
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.75rem;
    }
    .metric-label {
        font-size: 0.75rem; color: #6b7084; text-transform: uppercase;
        letter-spacing: 0.8px; font-weight: 600; margin-bottom: 0.4rem;
    }
    .metric-value {
        font-size: 1.6rem; font-weight: 700; color: #ffffff;
    }
    .metric-sub { font-size: 0.8rem; color: #8b8fa3; margin-top: 0.2rem; }

    /* Phase Cards */
    .phase-card {
        background: #1a1d27; border: 1px solid #2a2d3a;
        border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.6rem;
    }
    .phase-title {
        font-size: 0.85rem; font-weight: 600; color: #ffffff;
        margin-bottom: 0.3rem;
    }
    .phase-time {
        font-size: 0.75rem; color: #6366f1; font-weight: 500;
    }
    .phase-desc { font-size: 0.78rem; color: #8b8fa3; margin-top: 0.3rem; }

    /* Frame Preview */
    .frame-item {
        background: #1a1d27; border: 1px solid #2a2d3a;
        border-radius: 10px; overflow: hidden; margin-bottom: 0.8rem;
    }
    .frame-time-tag {
        background: rgba(99,102,241,0.15); color: #818cf8;
        font-size: 0.72rem; font-weight: 600; padding: 0.3rem 0.8rem;
        display: inline-block; border-radius: 20px; margin: 0.5rem 0.6rem 0 0.6rem;
    }
    .frame-tags { padding: 0.4rem 0.6rem 0.6rem; }
    .frame-tag {
        display: inline-block; background: #232636; border: 1px solid #2a2d3a;
        color: #a1a1aa; font-size: 0.7rem; border-radius: 6px;
        padding: 0.2rem 0.5rem; margin: 0.2rem 0.2rem 0 0;
    }
    .frame-tag.red { background: rgba(239,68,68,0.15); border-color: rgba(239,68,68,0.3); color: #fca5a5; }
    .frame-tag.blue { background: rgba(59,130,246,0.15); border-color: rgba(59,130,246,0.3); color: #93c5fd; }
    .frame-tag.green { background: rgba(16,185,129,0.15); border-color: rgba(16,185,129,0.3); color: #6ee7b7; }
    .frame-tag.yellow { background: rgba(245,158,11,0.15); border-color: rgba(245,158,11,0.3); color: #fcd34d; }

    /* Section Title */
    .section-title {
        font-size: 1.05rem; font-weight: 600; color: #ffffff;
        margin: 1.5rem 0 0.8rem 0; padding-bottom: 0.5rem;
        border-bottom: 1px solid #2a2d3a;
    }

    /* Color Bar */
    .color-bar {
        display: flex; gap: 4px; align-items: center; margin: 0.3rem 0;
    }
    .color-swatch {
        width: 14px; height: 14px; border-radius: 3px; display: inline-block;
    }

    /* Table styling */
    table { width: 100%; border-collapse: collapse; }
    th { color: #6b7084; font-size: 0.72rem; text-transform: uppercase;
         letter-spacing: 0.5px; padding: 0.5rem 0.75rem; text-align: left;
         border-bottom: 1px solid #2a2d3a; }
    td { color: #d1d5db; font-size: 0.82rem; padding: 0.5rem 0.75rem;
         border-bottom: 1px solid #1e2130; }
    tr:hover td { background: #1a1d27; }

    /* Progress bars */
    .stProgress > div > div > div { background: #6366f1; }

    /* Status badge */
    .badge {
        display: inline-block; padding: 0.15rem 0.6rem; border-radius: 20px;
        font-size: 0.72rem; font-weight: 600;
    }
    .badge-success { background: rgba(16,185,129,0.15); color: #6ee7b7; }
    .badge-warning { background: rgba(245,158,11,0.15); color: #fcd34d; }
    .badge-danger { background: rgba(239,68,68,0.15); color: #fca5a5; }
    .badge-info { background: rgba(59,130,246,0.15); color: #93c5fd; }

    /* Upload area */
    .upload-zone {
        border: 2px dashed #2a2d3a; border-radius: 16px;
        padding: 3rem 2rem; text-align: center;
        transition: border-color 0.3s;
    }

    /* Hide default streamlit elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stToolbar"] { display: none; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0f1117; }
    ::-webkit-scrollbar-thumb { background: #2a2d3a; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────
def md5_path(video_bytes: bytes) -> str:
    return hashlib.md5(video_bytes).hexdigest()[:12]


@st.cache_data(ttl=300, show_spinner=False)
def cached_analysis(video_bytes: bytes):
    return run_full_analysis(video_bytes)


def get_tone_name(r: int, g: int, b: int) -> str:
    hsv = np.array([[[int(b/2), int((max(r,g,b)-min(r,g,b))*255/255), max(r,g,b)]]], dtype=np.uint8)
    hsv = cv2.cvtColor(hsv, cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])
    if v < 40: return '黑色'
    if s < 15 and v > 200: return '白色'
    if s < 30: return '灰色'
    if h < 10 or h >= 165: return '红色'
    if h < 25: return '橙色'
    if h < 35: return '黄色'
    if h < 70: return '绿色'
    if h < 100: return '青色'
    if h < 130: return '蓝色'
    if h < 155: return '紫色'
    return '粉色'


def extract_colors(frame, n=5):
    small = cv2.resize(frame, (80, 80))
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    pixels = rgb.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(pixels, n, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    counts = np.bincount(labels.flatten())
    order = np.argsort(-counts)
    result = []
    for idx in order:
        cr, cg, cb = int(centers[idx][0]), int(centers[idx][1]), int(centers[idx][2])
        result.append((get_tone_name(cr, cg, cb), (cr, cg, cb)))
    return result


def detect_scene_change(prev, curr, threshold=35):
    gray_prev = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    gray_curr = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray_prev, gray_curr)
    return diff.mean() > threshold, diff.mean()


def run_full_analysis(video_bytes: bytes):
    """Full video analysis pipeline."""
    tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    tmp.write(video_bytes)
    tmp.flush()
    video_path = tmp.name

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total / fps if fps > 0 else 0
    has_audio = cap.get(cv2.CAP_PROP_AUDIO_STREAM) >= 0
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = ''.join([chr((fourcc_int >> 8*i) & 0xFF) for i in range(4)])
    cap.release()
    file_size = len(video_bytes) / (1024 * 1024)

    # ── Frame Sampling ─────────────────────────────────────────
    sample_interval = max(1.0, duration / 10)
    sample_times = [round(t * sample_interval, 1)
                    for t in range(int(duration / sample_interval))]
    if sample_times and sample_times[-1] < duration - 1:
        sample_times.append(round(duration - 1, 1))
    sample_times = sorted(set(sample_times))

    frames_data = []
    scene_changes = []
    prev_frame = None
    prev_small = None
    cap = cv2.VideoCapture(video_path)

    for t in sample_times:
        idx = int(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue

        # Scene change
        if prev_frame is not None:
            is_cut, score = detect_scene_change(prev_frame, frame)
            if is_cut:
                scene_changes.append((round(t, 1), round(score, 1)))

        # Colors
        colors = extract_colors(frame)
        color_names = [c[0] for c in colors]
        rgb_avg = frame[:,:,2].mean(), frame[:,:,1].mean(), frame[:,:,0].mean()
        brightness = (rgb_avg[0]*0.299 + rgb_avg[1]*0.587 + rgb_avg[2]*0.114) / 255

        # HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hue_mean = hsv[:,:,0].mean()
        sat_mean = hsv[:,:,1].mean()
        val_mean = hsv[:,:,2].mean()

        # Medical/skin analysis
        skin_mask = ((hsv[:,:,0] < 25) | ((hsv[:,:,0] > 0))) & \
                    (hsv[:,:,1] > 20) & (hsv[:,:,1] < 120) & \
                    (hsv[:,:,2] > 60) & (hsv[:,:,2] < 230)
        skin_ratio = round(skin_mask.mean(), 3)

        redness_mask = ((hsv[:,:,0] < 10) | (hsv[:,:,0] > 170)) & (hsv[:,:,1] > 80) & (hsv[:,:,2] > 60)
        redness_ratio = round(redness_mask.mean(), 3)

        blush_mask = ((hsv[:,:,0] >= 0) & (hsv[:,:,0] < 20)) & (hsv[:,:,1] > 60) & (hsv[:,:,1] < 150)
        blush_ratio = round(blush_mask.mean(), 3)

        white_mask = (hsv[:,:,2] > 230) & (hsv[:,:,1] < 30)
        white_ratio = round(white_mask.mean(), 3)

        blue_mask = (hsv[:,:,0] >= 90) & (hsv[:,:,0] <= 130) & (hsv[:,:,1] > 40)
        blue_ratio = round(blue_mask.mean(), 3)

        green_mask = (hsv[:,:,0] >= 35) & (hsv[:,:,0] < 75) & (hsv[:,:,1] > 60)
        green_ratio = round(green_mask.mean(), 3)

        # Motion
        motion = 0.0
        small = cv2.resize(frame, (64, 64))
        if prev_small is not None:
            gray_prev = cv2.cvtColor(prev_small, cv2.COLOR_BGR2GRAY).astype(float)
            gray_curr = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(float)
            motion = round(min(1.0, np.abs(gray_curr - gray_prev).mean() / 30.0), 3)
        prev_small = small

        # Text proxy
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        text_ratio = round(binary.sum() / 255 / (frame.shape[0]*frame.shape[1]) * 100, 2)
        has_text = text_ratio > 0.3

        # Save thumbnail
        thumb = cv2.resize(frame, (320, int(320 * height / width)))
        thumb_rgb = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)
        frames_data.append({
            't': round(t, 1), 'idx': idx,
            'thumb': thumb_rgb,
            'colors': color_names,
            'color_rgbs': colors,
            'brightness': round(brightness, 3),
            'hue': round(hue_mean, 1), 'sat': round(sat_mean, 1), 'val': round(val_mean, 1),
            'skin_ratio': skin_ratio,
            'redness_ratio': redness_ratio,
            'blush_ratio': blush_ratio,
            'white_ratio': white_ratio,
            'blue_ratio': blue_ratio,
            'green_ratio': green_ratio,
            'motion': motion,
            'text_ratio': text_ratio,
            'has_text': has_text,
            'motion_label': '低' if motion < 0.05 else ('中' if motion < 0.2 else '高'),
            'brightness_label': '明亮' if brightness > 0.6 else ('昏暗' if brightness < 0.3 else '适中'),
        })
        prev_frame = frame.copy()
    cap.release()

    # ── Phase Detection ────────────────────────────────────────
    def detect_phase(r):
        if r['blue_ratio'] > 0.05:
            return 'DEVICE_UI'
        if r['skin_ratio'] > 0.12:
            return 'TREATMENT'
        if r['white_ratio'] > 0.25:
            return 'CLINIC_ENV'
        if r['text_ratio'] > 5:
            return 'TEXT_OVERLAY'
        return 'TRANSITION'

    phases = []
    current_phase = None
    phase_start = None

    for r in frames_data:
        phase = detect_phase(r)
        if phase != current_phase:
            if current_phase is not None:
                phases.append({'name': current_phase, 'start': phase_start, 'end': r['t']})
            current_phase = phase
            phase_start = r['t']
    if current_phase:
        phases.append({'name': current_phase, 'start': phase_start, 'end': frames_data[-1]['t']})

    # Merge short phases
    merged = []
    for p in phases:
        if merged and p['name'] == merged[-1]['name']:
            merged[-1]['end'] = p['end']
        else:
            merged.append(p.copy())

    # Phase labels
    phase_label = {
        'TREATMENT': ('治疗画面', '#6ee7b7'),
        'DEVICE_UI': ('设备界面', '#93c5fd'),
        'CLINIC_ENV': ('诊所环境', '#fcd34d'),
        'TEXT_OVERLAY': ('字幕说明', '#c4b5fd'),
        'TRANSITION': ('转场', '#94a3b8'),
    }

    # ── Summary ────────────────────────────────────────────────
    brightness_vals = [r['brightness'] for r in frames_data]
    motion_vals = [r['motion'] for r in frames_data]
    avg_b = sum(brightness_vals) / len(brightness_vals)
    avg_m = sum(motion_vals) / len(motion_vals)

    # Content type detection
    content_type = 'MEDICAL_EDU'
    if avg_b > 0.65 and avg_m > 0.3:
        content_type = 'DYNAMIC_MOBILE'
    elif frames_data and frames_data[0]['brightness'] > 0.65:
        skin_max = max(r['skin_ratio'] for r in frames_data)
        blue_avg = sum(r['blue_ratio'] for r in frames_data) / len(frames_data)
        if blue_avg > 0.08:
            content_type = 'MEDICAL_EDU'
        elif skin_max > 0.12:
            content_type = 'PERSONAL_VLOG'
        else:
            content_type = 'PRODUCT_DEMO'

    # Color distribution
    all_colors = sum([r['colors'] for r in frames_data], [])
    from collections import Counter
    top_colors = Counter(all_colors).most_common(5)

    summary = {
        'duration': round(duration, 1),
        'fps': round(fps, 2),
        'width': width,
        'height': height,
        'total_frames': total,
        'file_size': round(file_size, 2),
        'codec': codec,
        'has_audio': has_audio,
        'scene_changes': scene_changes,
        'avg_brightness': round(avg_b, 3),
        'avg_motion': round(avg_m, 3),
        'content_type': content_type,
        'top_colors': top_colors,
        'phases': merged,
    }

    # Cleanup
    try:
        os.unlink(video_path)
    except Exception:
        pass

    return frames_data, summary, phases, phase_label


def render_color_bar(rgbs):
    html = '<div class="color-bar">'
    for name, (r, g, b) in rgbs:
        html += f'<span class="color-swatch" style="background:rgb({r},{g},{b})" title="{name} ({r},{g},{b})"></span>'
    html += '</div>'
    return html


# ── Main App ──────────────────────────────────────────────────
def main():
    # ── Header ──────────────────────────────────────────────
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        st.markdown("""
        <div style="font-size:2.2rem;margin-top:0.3rem;">🎬</div>
        """, unsafe_allow_html=True)
    with col_title:
        st.markdown('<div class="main-header">Video Content Analyzer</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">上传视频 → 智能分帧 → 多维度内容分析 → 文案结构提取</div>', unsafe_allow_html=True)

    # ── Sidebar Upload ───────────────────────────────────────
    with st.sidebar:
        st.markdown('### 📤 上传视频')
        st.markdown('支持 MP4 / MOV / AVI / MKV')
        video_file = st.file_uploader(
            '拖拽或点击上传',
            type=['mp4', 'mov', 'avi', 'mkv', 'webm'],
            label_visibility='collapsed'
        )
        st.markdown('---')
        st.markdown('### ⚙️ 分析设置')

        sample_mode = st.selectbox(
            '采样模式',
            ['自动（10帧）', '精细（20帧）', '快速（5帧）'],
            index=0
        )

        st.markdown('---')
        st.markdown('### 🧩 功能模块')
        st.checkbox('✅ 视频分帧预览', value=True, disabled=True)
        st.checkbox('✅ 内容分析报告', value=True, disabled=True)
        st.checkbox('✅ 文案结构拆解', value=True, disabled=True)
        st.checkbox('✅ 色彩趋势图表', value=True, disabled=True)

        st.markdown('---')
        st.markdown(f"""
        <div style="font-size:0.72rem;color:#6b7084;text-align:center;">
        Powered by OpenCV + NumPy<br/>
        &copy; 2025 Video Analyzer
        </div>
        """, unsafe_allow_html=True)

    # ── No Video State ────────────────────────────────────────
    if video_file is None:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric('支持的格式', 'MP4 / MOV / AVI / MKV', '')
        with col2:
            st.metric('分析维度', '颜色 · 运动 · 场景 · 文字', '')
        with col3:
            st.metric('输出类型', '帧预览 · 图表 · 结构报告', '')
        st.markdown('---')

        st.markdown('#### 📋 使用流程')
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown('**① 上传视频**\n\n点击左侧上传按钮，选择视频文件（支持拖拽）')
        with col_b:
            st.markdown('**② 智能分析**\n\n系统自动完成分帧、色彩分析、场景检测、文案结构提取')
        with col_c:
            st.markdown('**③ 查看报告**\n\n分帧预览 / 内容总结 / 文案拆解 / 趋势图表')

        st.markdown('---')
        st.markdown('#### 🧪 快速演示')
        demo_file = Path(__file__).parent / 'frames'
        if demo_file.exists():
            demos = list(demo_file.glob('u_*.jpg'))
            if demos:
                st.info(f'检测到 {len(demos)} 张已提取的帧（{demo_file.parent.name} 目录下），上传视频即可开始分析。')
        else:
            st.info('左侧上传视频文件开始分析')
        return

    # ── Load & Analyze ────────────────────────────────────────
    video_bytes = video_file.read()
    key = md5_path(video_bytes)

    with st.spinner('🔍 正在分析视频，请稍候...'):
        frames_data, summary, phases, phase_label = cached_analysis(video_bytes)

    # ── Video Info Bar ───────────────────────────────────────
    orientation = '竖屏 9:16' if summary['height'] > summary['width'] else '横屏 16:9'
    ratio = f"{summary['width']}×{summary['height']}"

    metric_cols = st.columns(6)
    with metric_cols[0]:
        st.metric('时长', f"{summary['duration']:.1f}s", orientation)
    with metric_cols[1]:
        st.metric('分辨率', ratio, '竖屏' if summary['height'] > summary['width'] else '横屏')
    with metric_cols[2]:
        st.metric('帧率', f"{summary['fps']:.0f}fps", summary['codec'])
    with metric_cols[3]:
        st.metric('总帧数', f"{summary['total_frames']:,}", '')
    with metric_cols[4]:
        st.metric('文件大小', f"{summary['file_size']:.1f}MB", '')
    with metric_cols[5]:
        audio_label = '有' if summary['has_audio'] else '无'
        st.metric('音轨', audio_label, '静音视频' if not summary['has_audio'] else '')

    st.markdown('---')

    # ── Tab Layout ────────────────────────────────────────────
    tab_overview, tab_frames, tab_analysis, tab_structure, tab_report = st.tabs([
        '📊 总览概览',
        '🖼️ 视频分帧',
        '📈 内容分析',
        '📝 文案结构',
        '📄 完整报告',
    ])

    # ════════════════════════════════════════════════════════
    # TAB 1: 总览概览
    # ════════════════════════════════════════════════════════
    with tab_overview:
        col_left, col_right = st.columns([1, 1])

        # Left: Key metrics
        with col_left:
            st.markdown('#### 🎯 核心指标')

            # Brightness gauge
            b = summary['avg_brightness']
            b_label = '明亮' if b > 0.6 else ('昏暗' if b < 0.3 else '适中')
            b_pct = int(b * 100)
            st.progress(b, text=f"平均亮度 {b_pct}% ({b_label})")

            # Motion gauge
            m = summary['avg_motion']
            m_label = '静止' if m < 0.05 else ('平稳' if m < 0.15 else '运动频繁')
            st.progress(min(1.0, m * 2), text=f"平均运动 {m:.3f} ({m_label})")

            # Color distribution
            st.markdown('##### 色调分布')
            for color_name, count in summary['top_colors'][:5]:
                pct = count / sum(c for _, c in summary['top_colors']) * 100
                st.markdown(f'**{color_name}** `{pct:.0f}%`')
                st.progress(min(pct / 100, 1.0), text='')

        # Right: Phase timeline
        with col_right:
            st.markdown('#### 🎬 场景时间线')

            timeline_html = '<div style="display:flex;flex-direction:column;gap:0.5rem;padding:0.5rem 0;">'
            for phase in phases:
                name = phase['name']
                label, color = phase_label.get(name, ('未知', '#94a3b8'))
                dur = phase['end'] - phase['start']
                width_pct = min(dur / summary['duration'] * 100, 100)
                timeline_html += f'''
                <div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.2rem;">
                        <span style="color:#e2e8f0;font-size:0.8rem;font-weight:600;">{label}</span>
                        <span style="color:#6366f1;font-size:0.72rem;">@{phase['start']:.0f}s - @{phase['end']:.0f}s</span>
                    </div>
                    <div style="background:#1e2130;border-radius:8px;height:28px;overflow:hidden;">
                        <div style="background:{color}33;border-left:3px solid {color};
                             height:100%;width:{width_pct:.1f}%;border-radius:8px;display:flex;align-items:center;padding-left:0.5rem;">
                            <span style="color:{color};font-size:0.7rem;font-weight:600;">{dur:.1f}s</span>
                        </div>
                    </div>
                </div>
                '''
            timeline_html += '</div>'
            st.markdown(timeline_html, unsafe_allow_html=True)

            # Scene changes
            if summary['scene_changes']:
                st.markdown(f'#### ⚡ 场景切换（{len(summary["scene_changes"])}处）')
                for t, score in summary['scene_changes']:
                    bar = '█' * min(10, int(score / 3))
                    st.markdown(f'@{t:.1f}s  变化得分 {score:.0f}  {bar}')
            else:
                st.success('未检测到明显场景切换')

    # ════════════════════════════════════════════════════════
    # TAB 2: 视频分帧
    # ════════════════════════════════════════════════════════
    with tab_frames:
        st.markdown('#### 🖼️ 关键帧预览')
        st.caption(f'共 {len(frames_data)} 帧，每帧自动附色彩分析')

        cols = st.columns(3)
        for i, fd in enumerate(frames_data):
            with cols[i % 3]:
                st.image(fd['thumb'], caption=f'@{fd["t"]:.1f}s', width=320)

                # Color swatches
                swatches_html = render_color_bar(fd['color_rgbs'][:3])
                st.markdown(swatches_html, unsafe_allow_html=True)

                # Tags
                tags_html = '<div style="display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.3rem;">'
                tags_html += f'<span class="frame-tag">{fd["brightness_label"]}</span>'
                tags_html += f'<span class="frame-tag">{fd["motion_label"]}运动</span>'
                if fd['has_text']:
                    tags_html += '<span class="frame-tag yellow">有文字</span>'
                if fd['blue_ratio'] > 0.05:
                    tags_html += '<span class="frame-tag blue">设备界面</span>'
                if fd['skin_ratio'] > 0.12:
                    tags_html += '<span class="frame-tag green">治疗画面</span>'
                tags_html += '</div>'
                st.markdown(tags_html, unsafe_allow_html=True)
                st.markdown('---')

    # ════════════════════════════════════════════════════════
    # TAB 3: 内容分析
    # ════════════════════════════════════════════════════════
    with tab_analysis:
        # ── Charts row 1 ──────────────────────────────────────
        c1, c2 = st.columns(2)

        with c1:
            st.markdown('##### 🎨 颜色趋势（色调H / 饱和度S / 明度V）')
            df_hsv = pd.DataFrame([{
                'Time': f'@{r["t"]:.0f}s',
                'Hue': r['hue'],
                'Saturation': r['sat'],
                'Brightness': r['val'],
            } for r in frames_data])

            fig_hsv = go.Figure()
            fig_hsv.add_trace(go.Scatter(x=df_hsv['Time'], y=df_hsv['Hue'],
                name='Hue', line=dict(color='#f87171', width=2), mode='lines+markers'))
            fig_hsv.add_trace(go.Scatter(x=df_hsv['Time'], y=df_hsv['Saturation'],
                name='Saturation', line=dict(color='#fbbf24', width=2), mode='lines+markers'))
            fig_hsv.add_trace(go.Scatter(x=df_hsv['Time'], y=df_hsv['Brightness'],
                name='Brightness', line=dict(color='#60a5fa', width=2), mode='lines+markers'))
            fig_hsv.update_layout(
                plot_bgcolor='#1a1d27', paper_bgcolor='#1a1d27',
                font_color='#e2e8f0', height=280,
                margin=dict(l=40, r=20, t=30, b=40),
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
            )
            fig_hsv.update_xaxes(gridcolor='#2a2d3a', color='#6b7084')
            fig_hsv.update_yaxes(gridcolor='#2a2d3a', color='#6b7084')
            st.plotly_chart(fig_hsv, use_container_width=True)

        with c2:
            st.markdown('##### 🧊 医学色彩分析（皮肤/红肿/设备蓝）')
            df_med = pd.DataFrame([{
                'Time': f'@{r["t"]:.0f}s',
                '皮肤': r['skin_ratio'] * 100,
                '红肿': r['redness_ratio'] * 100,
                '泛红': r['blush_ratio'] * 100,
                '设备蓝': r['blue_ratio'] * 100,
                '白色': r['white_ratio'] * 100,
            } for r in frames_data])

            fig_med = go.Figure()
            fig_med.add_trace(go.Bar(name='皮肤%', x=df_med['Time'], y=df_med['皮肤'],
                marker_color='#fca5a5', width=0.6))
            fig_med.add_trace(go.Bar(name='红肿%', x=df_med['Time'], y=df_med['红肿'],
                marker_color='#ef4444', width=0.6))
            fig_med.add_trace(go.Bar(name='设备蓝%', x=df_med['Time'], y=df_med['设备蓝'],
                marker_color='#3b82f6', width=0.6))
            fig_med.update_layout(
                barmode='group', plot_bgcolor='#1a1d27', paper_bgcolor='#1a1d27',
                font_color='#e2e8f0', height=280,
                margin=dict(l=40, r=20, t=30, b=40),
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                bargroupgap=0.1,
            )
            fig_med.update_xaxes(gridcolor='#2a2d3a', color='#6b7084')
            fig_med.update_yaxes(gridcolor='#2a2d3a', color='#6b7084')
            st.plotly_chart(fig_med, use_container_width=True)

        # ── Charts row 2 ──────────────────────────────────────
        c3, c4 = st.columns(2)

        with c3:
            st.markdown('##### 💡 亮度 & 运动趋势')
            df_bm = pd.DataFrame([{
                'Time': f'@{r["t"]:.0f}s',
                'Brightness': r['brightness'],
                'Motion': r['motion'],
            } for r in frames_data])

            fig_bm = go.Figure()
            fig_bm.add_trace(go.Scatter(x=df_bm['Time'], y=df_bm['Brightness'],
                name='亮度', line=dict(color='#fbbf24', width=2.5), fill='tozeroy',
                fillcolor='rgba(251,191,36,0.1)'))
            fig_bm.add_trace(go.Scatter(x=df_bm['Time'], y=df_bm['Motion'],
                name='运动', line=dict(color='#818cf8', width=2), yaxis='y2'))
            fig_bm.update_layout(
                plot_bgcolor='#1a1d27', paper_bgcolor='#1a1d27',
                font_color='#e2e8f0', height=280,
                margin=dict(l=40, r=20, t=30, b=40),
                yaxis2=dict(title='', overlaying='y', side='right', showgrid=False),
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
            )
            fig_bm.update_xaxes(gridcolor='#2a2d3a', color='#6b7084')
            fig_bm.update_yaxes(gridcolor='#2a2d3a', color='#6b7084')
            st.plotly_chart(fig_bm, use_container_width=True)

        with c4:
            st.markdown('##### 🏷️ 文字密度变化')
            df_text = pd.DataFrame([{
                'Time': f'@{r["t"]:.0f}s',
                'Text%': r['text_ratio'],
            } for r in frames_data])
            fig_text = go.Figure(go.Scatter(
                x=df_text['Time'], y=df_text['Text%'],
                mode='lines+markers', name='文字密度%',
                line=dict(color='#a78bfa', width=2.5),
                marker=dict(size=8, color='#a78bfa'),
                fill='tozeroy', fillcolor='rgba(167,139,250,0.1)'
            ))
            fig_text.update_layout(
                plot_bgcolor='#1a1d27', paper_bgcolor='#1a1d27',
                font_color='#e2e8f0', height=280,
                margin=dict(l=40, r=20, t=30, b=40),
                yaxis_title='文字密度 %',
            )
            fig_text.update_xaxes(gridcolor='#2a2d3a', color='#6b7084')
            fig_text.update_yaxes(gridcolor='#2a2d3a', color='#6b7084')
            st.plotly_chart(fig_text, use_container_width=True)

        # ── Data Table ─────────────────────────────────────────
        st.markdown('##### 📋 帧数据详情表')
        table_data = [{
            '时间': f'@{r["t"]:.1f}s',
            '主色调': ','.join(r['colors'][:3]),
            '亮度': f'{r["brightness"]:.2f}',
            '运动': r['motion_label'],
            '皮肤%': f'{r["skin_ratio"]*100:.1f}%',
            '设备蓝%': f'{r["blue_ratio"]*100:.1f}%',
            '红肿%': f'{r["redness_ratio"]*100:.1f}%',
            '文字%': f'{r["text_ratio"]:.1f}%',
            'Hue': f'{r["hue"]:.0f}',
            'Sat': f'{r["sat"]:.0f}',
        } for r in frames_data]
        st.dataframe(table_data, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════
    # TAB 4: 文案结构
    # ════════════════════════════════════════════════════════
    with tab_structure:
        st.markdown('#### 📝 视频文案结构拆解')

        # Phase analysis
        for phase in phases:
            name = phase['name']
            label, color = phase_label.get(name, ('未知', '#94a3b8'))
            dur = phase['end'] - phase['start']

            # Find relevant frames
            phase_frames = [r for r in frames_data
                            if phase['start'] <= r['t'] <= phase['end']]

            with st.container():
                st.markdown(f"""
                <div class="phase-card" style="border-left: 3px solid {color};">
                    <div class="phase-title" style="color: {color};">
                        {label}
                        <span style="float:right;font-size:0.72rem;color:#6b7084;">
                            @{phase['start']:.0f}s - @{phase['end']:.0f}s ({dur:.1f}s)
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_a, col_b = st.columns([1, 2])
                with col_a:
                    if phase_frames:
                        st.image(phase_frames[0]['thumb'], width=280)
                        st.caption(f'首帧 @{phase_frames[0]["t"]:.1f}s')
                with col_b:
                    # Content description
                    if name == 'DEVICE_UI':
                        desc = (
                            f'- 设备界面为主（蓝色占比均值: '
                            f'{sum(r["blue_ratio"] for r in phase_frames)/len(phase_frames)*100:.1f}%）\n'
                            f'- 文字密度: {sum(r["text_ratio"] for r in phase_frames)/len(phase_frames):.1f}%\n'
                            f'- 推断内容: 设备参数介绍 / 原理说明 / 技术讲解'
                        )
                    elif name == 'TREATMENT':
                        desc = (
                            f'- 治疗画面为主（皮肤占比均值: '
                            f'{sum(r["skin_ratio"] for r in phase_frames)/len(phase_frames)*100:.1f}%）\n'
                            f'- 红肿效果: {sum(r["redness_ratio"] for r in phase_frames)/len(phase_frames)*100:.1f}%\n'
                            f'- 推断内容: 治疗实操 / 分区讲解 / 术后效果展示'
                        )
                    elif name == 'CLINIC_ENV':
                        desc = (
                            f'- 诊所/环境画面为主（白色占比: '
                            f'{sum(r["white_ratio"] for r in phase_frames)/len(phase_frames)*100:.1f}%）\n'
                            f'- 推断内容: 诊所环境 / 设备展示 / 环境介绍'
                        )
                    elif name == 'TEXT_OVERLAY':
                        desc = (
                            f'- 文字说明为主（文字密度: '
                            f'{sum(r["text_ratio"] for r in phase_frames)/len(phase_frames):.1f}%）\n'
                            f'- 推断内容: 字幕讲解 / 卖点说明 / 步骤描述'
                        )
                    else:
                        desc = f'- 过渡/转场段落 ({dur:.1f}秒)'

                    st.markdown(f'<div style="font-size:0.82rem;color:#8b8fa3;line-height:1.8;padding:0.5rem 0;">{desc}</div>', unsafe_allow_html=True)

                    # Key metrics for phase
                    if phase_frames:
                        avg_b = sum(r['brightness'] for r in phase_frames) / len(phase_frames)
                        avg_sat = sum(r['sat'] for r in phase_frames) / len(phase_frames)
                        top_color = Counter(sum([r['colors'] for r in phase_frames], [])).most_common(1)[0]
                        st.markdown(f"""
                        <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:0.5rem;">
                            <span class="badge badge-info">亮度 {avg_b:.2f}</span>
                            <span class="badge badge-warning">饱和 {avg_sat:.0f}</span>
                            <span class="badge badge-success">主色 {top_color[0]}</span>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown('---')

        # Script template
        st.markdown('#### 📋 文案脚本模板（还原）')
        script_md = f"""
| 段落 | 时间区间 | 时长 | 内容类型 | 推断文案方向 |
|------|---------|------|---------|------------|
"""
        for phase in phases:
            label, _ = phase_label.get(phase['name'], ('未知', ''))
            dur = phase['end'] - phase['start']
            content_dir = {
                'DEVICE_UI': '设备原理 / 参数说明 / 技术讲解',
                'TREATMENT': '治疗实操 / 分区演示 / 效果描述',
                'CLINIC_ENV': '环境展示 / 资质介绍 / 设备展示',
                'TEXT_OVERLAY': '字幕讲解 / 卖点总结 / 步骤说明',
                'TRANSITION': '过渡 / 场景切换',
            }.get(phase['name'], '')
            script_md += f"| {label} | @{phase['start']:.0f}s-@{phase['end']:.0f}s | {dur:.1f}s | {phase['name']} | {content_dir} |\n"

        st.markdown(script_md)

    # ════════════════════════════════════════════════════════
    # TAB 5: 完整报告
    # ════════════════════════════════════════════════════════
    with tab_report:
        st.markdown('#### 📄 视频内容分析完整报告')

        report_md = f"""
# 视频内容分析报告

**文件**: {video_file.name}  
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**分析帧数**: {len(frames_data)} 帧

---

## 一、基本信息

| 属性 | 数值 |
|------|------|
| 时长 | {summary['duration']:.1f} 秒 |
| 分辨率 | {summary['width']} × {summary['height']} |
| 方向 | {'竖屏 9:16' if summary['height'] > summary['width'] else '横屏 16:9'} |
| 帧率 | {summary['fps']:.2f} fps |
| 编码 | {summary['codec']} |
| 总帧数 | {summary['total_frames']} |
| 文件大小 | {summary['file_size']:.2f} MB |
| 音轨 | {'有' if summary['has_audio'] else '无（静音视频）'} |

---

## 二、核心分析指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 平均亮度 | {summary['avg_brightness']:.3f} | {'明亮' if summary['avg_brightness'] > 0.6 else ('昏暗' if summary['avg_brightness'] < 0.3 else '适中')} |
| 平均运动 | {summary['avg_motion']:.3f} | {'静止' if summary['avg_motion'] < 0.05 else ('平稳' if summary['avg_motion'] < 0.15 else '运动频繁')} |
| 场景切换 | {len(summary['scene_changes'])} 处 | {'有剪辑点' if summary['scene_changes'] else '画面连续'} |
| 色调主色 | {summary['top_colors'][0][0] if summary['top_colors'] else 'N/A'} | 出现 {summary['top_colors'][0][1]} 次 |

---

## 三、场景时间线

"""
        for phase in phases:
            label, _ = phase_label.get(phase['name'], ('未知', ''))
            dur = phase['end'] - phase['start']
            report_md += f"- **{label}** (@{phase['start']:.0f}s - @{phase['end']:.0f}s, {dur:.1f}s)\n"

        report_md += f"""
---

## 四、帧分析数据

| 时间 | 主色调 | 亮度 | 运动 | 皮肤% | 设备蓝% | 红肿% | 文字% |
|------|--------|------|------|-------|--------|-------|-------|
"""
        for r in frames_data:
            report_md += f"| @{r['t']:.1f}s | {','.join(r['colors'][:3])} | {r['brightness']:.2f} | {r['motion_label']} | {r['skin_ratio']*100:.1f}% | {r['blue_ratio']*100:.1f}% | {r['redness_ratio']*100:.1f}% | {r['text_ratio']:.1f}% |\n"

        report_md += """
---

## 五、内容类型判断

"""
        content_desc = {
            'MEDICAL_EDU': '医疗美容科普（设备讲解 + 治疗实操）',
            'PERSONAL_VLOG': '个人vlog / 竖屏种草',
            'PRODUCT_DEMO': '产品演示 / 电商视频',
            'DYNAMIC_MOBILE': '动态内容 / 移动跟拍',
        }.get(summary['content_type'], '未知类型')

        report_md += f"**内容类型**: {content_desc}\n\n"

        report_md += f"""
---

*报告由 Video Content Analyzer 自动生成
Powered by OpenCV + NumPy + Plotly*
"""

        st.markdown(report_md)

        # Download button
        st.download_button(
            '📥 下载完整报告 (Markdown)',
            report_md.encode('utf-8'),
            file_name=f'video_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md',
            mime='text/markdown',
        )

        # Download frames as zip
        st.markdown('#### 🖼️ 帧图片打包下载')
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for r in frames_data:
                img_bytes = cv2.imencode('.jpg', cv2.cvtColor(r['thumb'], cv2.COLOR_RGB2BGR))[1].tobytes()
                zf.writestr(f'frame_{r["t"]:04.1f}s.jpg', img_bytes)
        buf.seek(0)
        st.download_button(
            '📦 下载全部帧图片 (ZIP)',
            buf.getvalue(),
            file_name=f'video_frames_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
            mime='application/zip',
        )


# ── Entry ─────────────────────────────────────────────────────
if __name__ == '__main__':
    main()
