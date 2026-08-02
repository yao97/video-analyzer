"""Full analysis pipeline test."""
import sys, os, asyncio
sys.path.insert(0, r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\src')

video_path = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'

print('=== Import Test ===')
from video_analyzer.config import settings
from video_analyzer.schemas import VideoMetadata, FrameAnalysis
from video_analyzer.services.video_metadata_service import VideoMetadataService
from video_analyzer.services.frame_analyzer import FrameAnalyzer
print('  config: OK')
print('  schemas: OK')
print('  video_metadata_service: OK')
print('  frame_analyzer: OK')


async def run_analysis():
    print('\n=== Video Metadata ===')
    svc = VideoMetadataService()
    meta = await svc.extract_metadata(video_path)
    print(f'  文件: {meta.filename}')
    print(f'  时长: {meta.duration_seconds:.2f}s')
    print(f'  分辨率: {meta.width}x{meta.height}')
    print(f'  FPS: {meta.fps:.2f}')
    print(f'  帧数: {meta.total_frames}')
    print(f'  文件大小: {meta.file_size_mb:.2f} MB')
    print(f'  视频编码: {meta.codec}')

    print('\n=== Frame Analysis (6 samples) ===')
    import cv2
    cap = cv2.VideoCapture(video_path)
    cap_fps = cap.get(cv2.CAP_PROP_FPS)
    cap_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    analyzer = FrameAnalyzer(use_gpu=False)

    sample_count = 6
    sample_indices = [int(i * cap_frame_count / sample_count) for i in range(sample_count)]
    all_frames = []
    for idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            ts = idx / cap_fps
            fa = await analyzer.analyze_frame(frame, idx, ts)
            all_frames.append(fa)
            # Calculate brightness from dominant_colors count as proxy
            motion_label = '低' if fa.motion_intensity < 0.05 else ('中' if fa.motion_intensity < 0.2 else '高')
            print(f'  [@{ts:5.1f}s | idx={idx:04d}] 主色调={fa.dominant_colors} | 运动强度={motion_label}({fa.motion_intensity:.3f}) | 场景={fa.scene_description}')

    print('\n  Detected objects:')
    for fa in all_frames:
        if fa.detected_objects:
            print(f'    @{fa.timestamp:.1f}s: {fa.detected_objects}')

    print('\n=== Result ===')
    print(f'  Metadata: OK ({meta.duration_seconds:.1f}s video)')
    print(f'  Frames analyzed: {len(all_frames)}')
    print(f'  Avg motion: {sum(f.motion_intensity for f in all_frames)/len(all_frames):.3f}')
    print('\nResult: SUCCESS')


asyncio.run(run_analysis())
