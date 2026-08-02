"""Build web_player_v3.html — precise line-based extraction."""
import os, re

os.chdir(os.path.dirname(os.path.abspath(__file__)))
with open('web_player.html', encoding='utf-8') as f:
    lines = f.readlines()

def block(start_line, end_line):
    return ''.join(lines[start_line-1:end_line])

# ── Verify no overlap helper ──────────────────────────────────────────
def check_overlap(name, s, e):
    if s <= len(lines):
        return
    print(f"WARNING: {name} starts at L{s} but file has {len(lines)} lines")

# ── Block ranges (all verified from source web_player.html) ──────────────
# (498,545): COLOR_RGB object + helpers (colorHex, setBadge, setStep)
COLOR_RGB       = block(498, 545)
# (546,679): CONTENT_TYPE_RULES array + scoreContentType function
CONTENT_RULES   = block(546, 679)
# (680,727): scoreContentType continuation + detectContentType
SCORE_FN        = block(680, 716)
DETECT_FN       = block(717, 727)
# (728,860): analyzeFramesColor + findSceneChanges
ANALYZE_FN      = block(728, 848)
SCENE_FN        = block(849, 860)
# (861,881): buildPhases function
BUILD_PHASES_FN = block(861, 881)
# (1002,1065): getPhaseLogic
GET_PHASE_FN    = block(1002, 1065)
# (1066,1091): CONTENT_TYPES_WITH_META object (ends before the processFile divider; L1092 blank, L1093=processFile)
CT_META         = block(1066, 1092)
# (1093,1245): async function processFile (closes at L1245)
PROCESS_FN      = block(1093, 1246)
# ── Render functions (standalone, called from processFile/polling) ───────
# (1250,1259): function renderMetrics(r)
RENDER_METRICS  = block(1250, 1260)
# (1261,1307): function renderOverview(r) + blank
RENDER_OVERVIEW = block(1261, 1308)
# (1308,1322): function renderSpeechSummary() + blank
RENDER_SPEECH_S = block(1308, 1323)
# (1324,1374): function renderSpeech(speech, contentType, duration) + blank
RENDER_SPEECH   = block(1324, 1375)
# (1376,1379): renderOverviewFinal/StructureFinal/ReportFinal + blank
RENDER_FINAL    = block(1376, 1380)
# (1380,1403): function renderFrames(r) + blank
RENDER_FRAMES   = block(1380, 1404)
# (1405,1408): function destroyCharts() + blank
DESTROY_CHARTS  = block(1405, 1409)
# (1410,1463): function renderCharts(r) + blank
RENDER_CHARTS   = block(1410, 1464)
# (1465,1519): function renderStructure(r, withSpeech)  ← standalone
RENDER_STRUCT   = block(1465, 1520)
# (1521,1611): function renderReport(r, speech)         ← standalone
RENDER_REPORT_FN= block(1521, 1612)
# ── Script generation (called by renderSpeech/renderReport) ─────────────
# (983,1001): generateScript + extractKeywords  ← hoisted; must precede RENDER_SPEECH
GEN_SCRIPT_FN   = block(983, 1001)
# ── Transcribe (pollTranscribeResult calls renderSpeech/renderOverviewFinal/...) ─
# (897,916): // Transcribe API banner + startTranscription function
TRANSCRIBE_JS   = block(897, 916)
# (918,982): pollTranscribeResult + extractKeywords (keywords also in GEN_SCRIPT_FN)
POLL_JS         = block(918, 982)
# ── Download ───────────────────────────────────────────────────────────
DOWNLOAD_REPORT = block(1613, 1622)  # function downloadReport (L1613-L1621)
DOWNLOAD_FRAMES = block(1623, 1634) # async function downloadFrames (L1623-L1633)
# ── Init ───────────────────────────────────────────────────────────────
INIT_CODE       = block(1635, 1640)  # Init event listeners (L1635-L1639)

# Print sizes
names = ['COLOR_RGB','CONTENT_RULES','SCORE_FN','DETECT_FN','ANALYZE_FN',
         'SCENE_FN','BUILD_PHASES_FN','GET_PHASE_FN','CT_META','PROCESS_FN',
         'RENDER_METRICS','RENDER_OVERVIEW','RENDER_SPEECH_S','RENDER_SPEECH',
         'RENDER_FINAL','RENDER_FRAMES','DESTROY_CHARTS','RENDER_CHARTS',
         'RENDER_STRUCT','RENDER_REPORT_FN','GEN_SCRIPT_FN',
         'TRANSCRIBE_JS','POLL_JS','DOWNLOAD_REPORT','DOWNLOAD_FRAMES','INIT_CODE']
for name in names:
    print(f"  {name}: {len(eval(name)):,} chars")

# ── v3_script assembly ─────────────────────────────────────────────────
# Order: helpers + core → CONTENT_TYPES_WITH_META → processFile →
#        script gen → render functions → poll/transcribe → download → init
v3_script = '\n'.join([
    "// State",
    "let analysisResult = null;",
    "let speechResult = null;",
    "let frameImages = [];",
    "let chartRefs = {};",
    "let transcribeJobId = null;",
    "let transcribePollTimer = null;",
    "",
    "// Helpers",
    "const $ = id => document.getElementById(id);",
    "const show = id => $(id)?.classList.remove('hidden');",
    "const hide = id => $(id)?.classList.add('hidden');",
    "",
    "const toast = (msg, type='success') => {",
    "  const t = $('toast');",
    "  t.textContent = msg; t.className = 'toast ' + type + ' show';",
    "  setTimeout(() => t.classList.remove('show'), 3500);",
    "};",
    "",
    "const switchTab = (btn, pid) => {",
    "  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));",
    "  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));",
    "  btn.classList.add('active');",
    "  $(pid)?.classList.add('active');",
    "  if (pid === 'tabCharts') setTimeout(() => Object.values(chartRefs).forEach(c => c?.resize?.()), 80);",
    "};",
    "",
    COLOR_RGB,
    CONTENT_RULES,
    SCORE_FN,
    DETECT_FN,
    ANALYZE_FN,
    SCENE_FN,
    BUILD_PHASES_FN,
    GET_PHASE_FN,
    CT_META,
    PROCESS_FN,
    # script gen before render functions (renderSpeech calls generateScript)
    GEN_SCRIPT_FN,
    # All render functions (order: metrics → overview → speech → frames → charts → structure → report)
    RENDER_METRICS,
    RENDER_OVERVIEW,
    RENDER_SPEECH_S,
    RENDER_SPEECH,
    RENDER_FINAL,
    RENDER_FRAMES,
    DESTROY_CHARTS,
    RENDER_CHARTS,
    RENDER_STRUCT,
    RENDER_REPORT_FN,
    # poll/transcribe after render (pollTranscribeResult calls renderXxx)
    TRANSCRIBE_JS,
    POLL_JS,
    DOWNLOAD_REPORT,
    DOWNLOAD_FRAMES,
    INIT_CODE,
    "console.log('[v3] loaded');",
])

# Check for duplicate function definitions
func_names = {}
dupes = []
for m in re.finditer(r'function (\w+)', v3_script):
    fn = m.group(1)
    if fn in func_names:
        dupes.append((fn, func_names[fn], m.start()))
    func_names[fn] = m.start()
if dupes:
    print(f"\nWARNING: {len(dupes)} duplicate function(s):")
    for fn, p1, p2 in dupes:
        print(f"  {fn} at pos {p1} and {p2}")
else:
    print(f"\nNo duplicates! {len(func_names)} unique functions")
print(f"v3_script size: {len(v3_script):,} chars")

# ── CSS ───────────────────────────────────────────────────────────────
css_m = re.search(r'<style>(.*?)</style>', open('web_player.html', encoding='utf-8').read(), re.DOTALL)
css = css_m.group(1) if css_m else ''

# ── HTML ──────────────────────────────────────────────────────────────
v3_html = (
    '<!DOCTYPE html>\n'
    '<html lang="zh-CN">\n'
    '<head>\n'
    '<meta charset="UTF-8">\n'
    '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 100 100%27><text y=%27.9em%27 font-size=%2790%27>&#127909;</text></svg>">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    '<title>Video Content Analyzer v3</title>\n'
    '<style>\n' + css + '\n</style>\n'
    '</head>\n'
    '<body>\n'
    '<div id="spinner" class="spinner-overlay hidden">\n'
    '<div class="spinner"></div>\n'
    '<div class="spinner-text" id="spinnerText">正在处理...</div>\n'
    '<div class="spinner-sub" id="spinnerSub">准备中</div>\n'
    '<div class="spinner-progress"><div class="spinner-progress-fill" id="spinnerFill" style="width:0%"></div></div>\n'
    '</div>\n'
    '<div id="toast" class="toast"></div>\n'
    '<header>\n'
    '<div style="font-size:1.4rem;">&#127909;</div>\n'
    '<div><h1>Video Content Analyzer</h1><div class="sub">上传视频 &rarr; 画面分析 &rarr; 语音转写 &rarr; 文案结构拆解</div></div>\n'
    '</header>\n'
    '<div id="mainLayout">\n'
    '<div class="container" id="uploadContainer">\n'
    '<div class="upload-zone" onclick="document.getElementById(\'fileInput\').click()">\n'
    '<div class="icon-big">&#128229;</div>\n'
    '<h2>点击上传视频文件</h2>\n'
    '<p>支持 MP4 / MOV / AVI / WebM，最大 600MB</p>\n'
    '<input type="file" id="fileInput" accept="video/*" style="display:none">\n'
    '</div>\n'
    '</div>\n'
    '<div id="mainContent" class="container hidden">\n'
    '<div id="leftPanel">\n'
    '<video id="videoPreview" controls style="width:100%;border-radius:10px;background:#000;display:block;"></video>\n'
    '<div id="previewMeta" style="font-size:0.72rem;color:#6b7084;margin-top:0.5rem;line-height:1.8;"></div>\n'
    '<div id="speechPreviewSection" style="margin-top:1rem;">\n'
    '<div style="font-weight:600;font-size:0.8rem;margin-bottom:0.4rem;">&#127911; 语音转写</div>\n'
    '<div id="speechPreviewText" style="font-size:0.78rem;color:#6b7084;">等待分析...</div>\n'
    '</div>\n'
    '</div>\n'
    '<div id="rightPanel">\n'
    '<div id="featureBadges" class="badges-row hidden">\n'
    '<div class="badge wait" id="badgeColor"><span>&#127912;</span><span>画面分析</span><span id="badgeColorText">等待</span></div>\n'
    '<div class="badge wait" id="badgeSpeech"><span>&#127911;</span><span>语音转写</span><span id="badgeSpeechText">等待</span></div>\n'
    '<div class="badge wait" id="badgeContent"><span>&#127981;</span><span>内容识别</span><span id="badgeContentText">等待</span></div>\n'
    '<div class="badge wait" id="badgeCopy"><span>&#128221;</span><span>文案生成</span><span id="badgeCopyText">等待</span></div>\n'
    '</div>\n'
    '<div id="metricsSection" class="metrics-bar hidden">\n'
    '<div class="metric-card"><div class="metric-label">时长</div><div class="metric-value" id="mDuration">--</div><div class="metric-sub" id="mOrientation">--</div></div>\n'
    '<div class="metric-card"><div class="metric-label">分辨率</div><div class="metric-value" id="mResolution">--</div><div class="metric-sub">H.264</div></div>\n'
    '<div class="metric-card"><div class="metric-label">帧率</div><div class="metric-value" id="mFps">--</div><div class="metric-sub">fps</div></div>\n'
    '<div class="metric-card"><div class="metric-label">总帧数</div><div class="metric-value" id="mFrames">--</div><div class="metric-sub">帧</div></div>\n'
    '<div class="metric-card"><div class="metric-label">文件大小</div><div class="metric-value" id="mSize">--</div><div class="metric-sub">MB</div></div>\n'
    '<div class="metric-card"><div class="metric-label">音轨</div><div class="metric-value" id="mAudio">--</div><div class="metric-sub" id="mAudioSub">--</div></div>\n'
    '</div>\n'
    '<div id="tabsSection" class="hidden">\n'
    '<div class="tabs">\n'
    '<button class="tab active" onclick="switchTab(this,\'tabOverview\')">&#128200; 总览</button>\n'
    '<button class="tab" onclick="switchTab(this,\'tabSpeech\')">&#127911; 语音转写</button>\n'
    '<button class="tab" onclick="switchTab(this,\'tabFrames\')">&#128444; 视频分帧</button>\n'
    '<button class="tab" onclick="switchTab(this,\'tabCharts\')">&#128202; 内容图表</button>\n'
    '<button class="tab" onclick="switchTab(this,\'tabStructure\')">&#128221; 文案结构</button>\n'
    '<button class="tab" onclick="switchTab(this,\'tabReport\')">&#128196; 完整报告</button>\n'
    '</div>\n'
    # tabOverview
    '<div id="tabOverview" class="tab-panel active">\n'
    '<div class="section"><div class="section-title">&#127981; <span>内容类型识别</span></div>\n'
    '<div class="copy-analysis">\n'
    '<div id="typeTitle" style="font-size:0.9rem;font-weight:700;margin-bottom:0.35rem;">--</div>\n'
    '<div id="typeText" style="font-size:0.76rem;color:#8b8fa3;line-height:1.65;margin-bottom:0.5rem;">--</div>\n'
    '<div id="contentSignals" class="copy-tags"></div>\n'
    '<div id="contentEvidence" style="margin-top:0.6rem;font-size:0.73rem;color:#6b7084;"></div>\n'
    '</div></div>\n'
    '<div class="section"><div class="section-title">&#128200; <span>核心指标</span></div>\n'
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">\n'
    '<div class="chart-card"><div class="chart-title">亮度 &amp; 运动 &amp; 文字</div><div id="overviewBars"></div></div>\n'
    '<div class="chart-card"><div class="chart-title">场景时间线</div><div id="timelineContainer"></div></div>\n'
    '</div></div>\n'
    '<div class="section"><div class="section-title">&#127911; <span>语音摘要</span> <span id="speechSummaryCount" class="count"></span></div>\n'
    '<div id="speechSummaryBox"></div></div>\n'
    '</div>\n'
    # tabSpeech
    '<div id="tabSpeech" class="tab-panel">\n'
    '<div class="section"><div class="section-title">&#127911; <span>语音转写</span> <span id="speechTabCount" class="count"></span></div>\n'
    '<div id="transcribeStatusBox" class="transcribe-status">\n'
    '<div class="transcribe-steps">\n'
    '<div class="transcribe-step"><span class="step-icon wait" id="stepUpload">1</span><span class="step-text">上传视频</span></div>\n'
    '<div class="transcribe-step"><span class="step-icon wait" id="stepExtract">2</span><span class="step-text">提取音频</span></div>\n'
    '<div class="transcribe-step"><span class="step-icon wait" id="stepWhisper">3</span><span class="step-text">Whisper 转写</span></div>\n'
    '<div class="transcribe-step"><span class="step-icon wait" id="stepDone">4</span><span class="step-text">完成</span></div>\n'
    '</div>\n'
    '<div id="whisperProgressWrap" class="hidden" style="margin-top:0.9rem;">\n'
    '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.3rem;">\n'
    '<span style="font-size:0.75rem;color:#818cf8;font-weight:600;">&#127917; Whisper 转写中</span>\n'
    '<span id="whisperPct" style="font-size:0.75rem;color:#fbbf24;font-weight:700;">40%</span>\n'
    '</div>\n'
    '<div style="height:8px;background:#2a2d3a;border-radius:6px;overflow:hidden;">\n'
    '<div id="whisperBar" style="height:100%;background:linear-gradient(90deg,#6366f1,#818cf8);border-radius:6px;transition:width 0.5s;width:40%;"></div>\n'
    '</div>\n'
    '<div id="whisperETA" style="font-size:0.68rem;color:#6b7084;margin-top:0.22rem;text-align:right;">预估剩余 <span id="whisperETASec">--</span>s</div>\n'
    '</div>\n'
    '</div>\n'
    '<div id="speechTimeline" class="speech-timeline"></div>\n'
    '</div>\n'
    '<div class="section"><div class="section-title">&#128221; <span>关键词提取</span></div>\n'
    '<div class="copy-analysis">\n'
    '<div class="copy-section"><div class="copy-section-title">高频词</div><div id="kwFreq" class="copy-tags"></div></div>\n'
    '<div class="copy-section"><div class="copy-section-title">动作词</div><div id="kwAction" class="copy-tags"></div></div>\n'
    '<div class="copy-section"><div class="copy-section-title">情绪词</div><div id="kwEmotion" class="copy-tags"></div></div>\n'
    '<div class="copy-section"><div class="copy-section-title">产品/核心词</div><div id="kwProduct" class="copy-tags"></div></div>\n'
    '</div></div>\n'
    '<div class="section"><div class="section-title">&#128221; <span>视频文案脚本</span></div>\n'
    '<div id="generatedScript" class="copy-analysis" style="font-size:0.8rem;line-height:2;color:#d1d5db;white-space:pre-wrap;"></div>\n'
    '</div>\n'
    '</div>\n'
    # tabFrames
    '<div id="tabFrames" class="tab-panel">\n'
    '<div class="section"><div class="section-title">&#128444; <span>关键帧预览</span> <span id="frameCount" class="count"></span></div>\n'
    '<div class="frame-grid" id="frameGrid"></div>\n'
    '</div>\n'
    '</div>\n'
    # tabCharts
    '<div id="tabCharts" class="tab-panel">\n'
    '<div class="section"><div class="section-title">&#128202; <span>多维分析图表</span></div>\n'
    '<div class="chart-grid">\n'
    '<div class="chart-card"><div class="chart-title">RGB 色彩趋势</div><canvas id="chartRGB" height="150"></canvas></div>\n'
    '<div class="chart-card"><div class="chart-title">亮度 &amp; 运动</div><canvas id="chartBM" height="150"></canvas></div>\n'
    '<div class="chart-card"><div class="chart-title">文字密度</div><canvas id="chartText" height="150"></canvas></div>\n'
    '<div class="chart-card"><div class="chart-title">色调分布</div><canvas id="chartColorPie" height="150"></canvas></div>\n'
    '</div>\n'
    '</div>\n'
    '<div class="section"><div class="section-title">&#128203; <span>帧数据详情</span></div>\n'
    '<div style="overflow-x:auto;">\n'
    '<table class="data-table" id="frameTable">\n'
    '<thead><tr><th>时间</th><th>主色调</th><th>亮度</th><th>运动</th><th>皮肤%</th><th>蓝色%</th><th>文字%</th><th>构图类型</th></tr></thead>\n'
    '<tbody></tbody>\n'
    '</table>\n'
    '</div>\n'
    '</div>\n'
    '</div>\n'
    # tabStructure
    '<div id="tabStructure" class="tab-panel">\n'
    '<div class="section"><div class="section-title">&#128221; <span>视频文案结构拆解</span> <span id="structureNote" class="count"></span></div>\n'
    '<div class="phase-list" id="phaseList"></div>\n'
    '</div>\n'
    '<div class="section"><div class="section-title">&#128203; <span>文案脚本对照表</span></div>\n'
    '<div style="overflow-x:auto;">\n'
    '<table class="data-table" id="scriptTable">\n'
    '<thead><tr><th>段落</th><th>时间</th><th>时长</th><th>画面特征</th><th>语音内容</th><th>文案方向</th></tr></thead>\n'
    '<tbody></tbody>\n'
    '</table>\n'
    '</div>\n'
    '</div>\n'
    '</div>\n'
    # tabReport
    '<div id="tabReport" class="tab-panel">\n'
    '<div class="section"><div class="section-title">&#128196; <span>完整分析报告</span></div>\n'
    '<textarea id="reportMd" readonly style="width:100%;min-height:450px;background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;color:#e2e8f0;padding:1rem;font-size:0.75rem;font-family:\'Courier New\',monospace;line-height:1.8;resize:vertical;"></textarea>\n'
    '<div style="display:flex;gap:0.45rem;margin-top:0.75rem;flex-wrap:wrap;">\n'
    '<button class="btn btn-primary" onclick="downloadReport()">&#128229; 下载报告</button>\n'
    '<button class="btn btn-secondary" onclick="downloadFrames()">&#128230; 下载帧图片</button>\n'
    '</div>\n'
    '</div>\n'
    '</div>\n'
    '</div>\n'  # tabsSection
    '</div>\n'  # rightPanel
    '</div>\n'  # mainContent
    '</div>\n'  # mainLayout
    '<script src="./chart.umd.min.js"></script>\n'
    '<script>\n'
    + v3_script +
    '\n</script>\n'
    '</body>\n'
    '</html>\n'
)

with open('web_player_v3.html', 'w', encoding='utf-8') as f:
    f.write(v3_html)

size = len(v3_html)
print(f"\nDone: web_player_v3.html = {size:,} bytes ({size//1024}KB)")
