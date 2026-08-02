with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', encoding='utf-8') as f:
    content = f.read()

# Add label, icon, color to each type in CONTENT_TYPE_RULES
# Need to add these fields after the type name (before weight)

replacements = [
    # ECOMMERCE
    ('  ECOMMERCE: {\n    weight:', '  ECOMMERCE: {\n    label: "电商带货", icon: "&#128722;", color: "#f87171",\n    weight:'),
    # VLOG
    ('  VLOG: {\n    weight:', '  VLOG: {\n    label: "Vlog/生活", icon: "&#128248;", color: "#f472b6",\n    weight:'),
    # MEDICAL
    ('  MEDICAL: {\n    weight:', '  MEDICAL: {\n    label: "医疗/医美", icon: "&#128138;", color: "#60a5fa",\n    weight:'),
    # FOOD
    ('  FOOD: {\n    weight:', '  FOOD: {\n    label: "美食/烹饪", icon: "&#127860;", color: "#fb923c",\n    weight:'),
    # EDUCATION
    ('  EDUCATION: {\n    weight:', '  EDUCATION: {\n    label: "教学/知识", icon: "&#128218;", color: "#a78bfa",\n    weight:'),
    # VIDEO_EDIT
    ('  VIDEO_EDIT: {\n    weight:', '  VIDEO_EDIT: {\n    label: "视频剪辑", icon: "&#9981;", color: "#6366f1",\n    weight:'),
    # LIVE_COMMERCE
    ('  LIVE_COMMERCE: {\n    weight:', '  LIVE_COMMERCE: {\n    label: "直播带货", icon: "&#128225;", color: "#ef4444",\n    weight:'),
    # SCREEN_RECORD
    ('  SCREEN_RECORD: {\n    weight:', '  SCREEN_RECORD: {\n    label: "屏幕录制", icon: "&#128421;", color: "#60a5fa",\n    weight:'),
    # ANIMATION
    ('  ANIMATION: {\n    weight:', '  ANIMATION: {\n    label: "动画/CG", icon: "&#127916;", color: "#a78bfa",\n    weight:'),
    # GENERAL
    ('  GENERAL: {\n    weight:', '  GENERAL: {\n    label: "通用内容", icon: "&#127909;", color: "#94a3b8",\n    weight:'),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new, 1)
        print(f'Replaced: {old[:50]}...')
    else:
        print(f'NOT FOUND: {old[:50]}...')

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('\nDone! Added label, icon, color to all content types.')
