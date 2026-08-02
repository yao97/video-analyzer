"""Audio transcription with Whisper."""
import whisper
import sys
sys.path.insert(0, r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\src')

video_path = r'C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4'

print('Loading Whisper tiny model...')
model = whisper.load_model('tiny')
print('Transcribing...')
result = model.transcribe(video_path, language='zh', verbose=False, temperature=0.0)
print('Language:', result.get('language'))
text = result.get('text', '').strip()
print('Text:', text)
segments = result.get('segments', [])
print('Segments count:', len(segments))
for seg in segments[:10]:
    start = seg['start']
    end = seg['end']
    txt = seg['text']
    print(f'  [{start:.1f}s - {end:.1f}s]: {txt}')
