path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# 1. Add new tab button (before 完整报告 tab)
old_tabs = '<button class="tab" onclick="switchTab(this,\'tabReport\')">&#128196; 完整报告</button>'
new_tabs = '<button class="tab" onclick="switchTab(this,\'tabShooting\')">&#127908; 拍摄手法</button>\n<button class="tab" onclick="switchTab(this,\'tabReport\')">&#128196; 完整报告</button>'
content = content.replace(old_tabs, new_tabs, 1)
print('[1/4] Added tab button')

# 2. Add tab panel HTML (before tabReport panel)
old_panel = '<div id="tabReport" class="tab-panel">'
new_panel = '''<div id="tabShooting" class="tab-panel">
  <div class="section">
    <div class="section-title">&#127908; 拍摄与剪辑手法分析</div>
    <div id="shootingContent" style="font-size:0.8rem;color:var(--muted);padding:1rem 0;">等待分析...</div>
  </div>
</div>

  <div id="tabReport" class="tab-panel">'''
content = content.replace(old_panel, new_panel, 1)
print('[2/4] Added tab panel HTML')

# 3. Add renderShooting function (before // ── Init ──)
render_fn = '''
// ═══════════════════════════════════════════════════════════════
// Shooting Technique Analysis
// ═══════════════════════════════════════════════════════════════
function renderShooting(r) {
  if (!r?.frames?.length) return;
  const frames = r.frames;
  const duration = r.duration;
  const sceneChanges = r.sceneChanges || [];
  
  // 1. 剪辑节奏
  const avgShotLen = sceneChanges.length > 0 ? duration / (sceneChanges.length + 1) : duration;
  const shotFreq = sceneChanges.length > 0 ? (sceneChanges.length + 1) / duration * 60 : 0;
  let rhythmLabel = '慢剪';
  let rhythmColor = '#60a5fa';
  if (avgShotLen < 2) { rhythmLabel = '快剪'; rhythmColor = '#ef4444'; }
  else if (avgShotLen < 5) { rhythmLabel = '正常'; rhythmColor = '#fbbf24'; }
  
  // 2. 景别分布
  const closeup = frames.filter(f => f.skinRatio > 0.15).length;
  const medium = frames.filter(f => f.skinRatio > 0.05 && f.skinRatio <= 0.15).length;
  const wide = frames.filter(f => f.skinRatio <= 0.05).length;
  const closeupPct = (closeup / frames.length * 100).toFixed(0);
  const mediumPct = (medium / frames.length * 100).toFixed(0);
  const widePct = (wide / frames.length * 100).toFixed(0);
  
  // 3. 镜头稳定性（motion 方差）
  const motions = frames.map(f => f.motion || 0);
  const avgMotion = motions.reduce((a,b)=>a+b,0) / motions.length;
  const motionVar = motions.reduce((a,b) => a + (b-avgMotion)**2, 0) / motions.length;
  let stabilityLabel = '稳定（三轴/固定）';
  let stabilityColor = '#4ade80';
  if (motionVar > 0.02) { stabilityLabel = '手持/运动'; stabilityColor = '#f87171'; }
  else if (motionVar > 0.005) { stabilityLabel = '轻微晃动'; stabilityColor = '#fbbf24'; }
  
  // 4. 光线风格
  const brights = frames.map(f => f.brightness);
  const avgBright = brights.reduce((a,b)=>a+b,0) / brights.length;
  const brightVar = brights.reduce((a,b) => a + (b-avgBright)**2, 0) / brights.length;
  let lightLabel = '光线平稳';
  let lightColor = '#4ade80';
  if (brightVar > 0.05) { lightLabel = '光线变化大（可能有跳剪/场景切换）'; lightColor = '#f87171'; }
  else if (avgBright < 0.35) { lightLabel = '偏暗（暗光/夜景）'; lightColor = '#6366f1'; }
  else if (avgBright > 0.7) { lightLabel = '明亮（日景/打光）'; lightColor = '#fbbf24'; }
  
  // 5. 色彩风格
  const sats = frames.map(f => f.sat || 0);
  const avgSat = sats.reduce((a,b)=>a+b,0) / sats.length;
  const hues = frames.map(f => f.hue || 0);
  const avgHue = hues.reduce((a,b)=>a+b,0) / hues.length;
  let colorLabel = '自然色调';
  let colorColor = '#4ade80';
  if (avgSat > 100) { colorLabel = '高饱和（鲜艳/动画）'; colorColor = '#a78bfa'; }
  else if (avgSat < 40) { colorLabel = '低饱和（胶片/复古）'; colorColor = '#94a3b8'; }
  if (avgHue < 30 || avgHue > 330) { colorLabel += ' / 暖色调'; colorColor = '#fb923c'; }
  else if (avgHue > 180 && avgHue < 270) { colorLabel += ' / 冷色调'; colorColor = '#60a5fa'; }
  
  // 6. 构图倾向（基于人物位置）
  const personFrames = frames.filter(f => f.skinRatio > 0.05);
  const hasPerson = personFrames.length > frames.length * 0.3;
  
  // Render
  $('shootingContent').innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:1rem;margin-bottom:1.5rem;">
      <div class="metric-card" style="border-color:${rhythmColor}33;">
        <div class="metric-label">剪辑节奏</div>
        <div class="metric-value" style="color:${rhythmColor}">${rhythmLabel}</div>
        <div class="metric-sub">${sceneChanges.length}次切换 | 平均${(avgShotLen).toFixed(1)}s/镜</div>
        <div class="metric-sub">切换频率: ${shotFreq.toFixed(1)}次/分钟</div>
      </div>
      <div class="metric-card" style="border-color:${stabilityColor}33;">
        <div class="metric-label">镜头稳定性</div>
        <div class="metric-value" style="color:${stabilityColor}">${stabilityLabel}</div>
        <div class="metric-sub">运动方差: ${motionVar.toFixed(4)}</div>
      </div>
      <div class="metric-card" style="border-color:${lightColor}33;">
        <div class="metric-label">光线风格</div>
        <div class="metric-value" style="color:${lightColor}">${lightLabel}</div>
        <div class="metric-sub">平均亮度: ${(avgBright*100).toFixed(0)}% | 变化${(brightVar*100).toFixed(1)}%</div>
      </div>
      <div class="metric-card" style="border-color:${colorColor}33;">
        <div class="metric-label">色彩风格</div>
        <div class="metric-value" style="color:${colorColor}">${colorLabel}</div>
        <div class="metric-sub">平均饱和度: ${avgSat.toFixed(0)} | 色相: ${avgHue.toFixed(0)}°</div>
      </div>
    </div>
    
    <div class="copy-analysis" style="margin-bottom:1.5rem;">
      <div class="copy-section-title">&#127911; 景别分布</div>
      <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
        <div class="copy-tag purple" style="flex:${closeupPct}">特写 ${closeupPct}%</div>
        <div class="copy-tag" style="flex:${mediumPct}">中景 ${mediumPct}%</div>
        <div class="copy-tag green" style="flex:${widePct}">全景/远景 ${widePct}%</div>
      </div>
      <div style="font-size:0.7rem;color:var(--muted);margin-top:0.3rem;">
        特写（人物占比>15%）: ${closeup}帧 | 中景（5-15%）: ${medium}帧 | 全景（<5%）: ${wide}帧
      </div>
    </div>
    
    ${hasPerson ? `
    <div class="copy-analysis" style="margin-bottom:1.5rem;">
      <div class="copy-section-title">&#128100; 人物构图</div>
      <div style="font-size:0.78rem;color:var(--muted);margin-top:0.5rem;line-height:1.8;">
        ${personFrames.length > 0 ? '人物主要出现在：' + (personFrames.filter(f => f.t < duration/3).length > 0 ? '开场 ' : '') + (personFrames.filter(f => f.t >= duration/3 && f.t < duration*2/3).length > 0 ? '中段 ' : '') + (personFrames.filter(f => f.t >= duration*2/3).length > 0 ? '结尾 ' : '') : '无明显人物主体'}
      </div>
    </div>` : ''}
    
    <div class="copy-analysis">
      <div class="copy-section-title">&#128161; 拍摄建议</div>
      <div style="font-size:0.76rem;color:var(--muted);margin-top:0.5rem;line-height:1.8;">
        ${rhythmLabel === '快剪' ? '&#10004; 快剪风格适合短视频平台（抖音/小红书），节奏紧凑<br>' : ''}
        ${stabilityLabel === '手持/运动' ? '&#10004; 手持拍摄增加真实感，但建议用稳定器提升质感<br>' : ''}
        ${lightLabel.includes('偏暗') ? '&#10004; 暗光环境建议补光或提升 ISO，避免噪点<br>' : ''}
        ${colorLabel.includes('高饱和') ? '&#10004; 高饱和色彩吸引眼球，适合美食/旅拍<br>' : ''}
        ${!hasPerson ? '&#10004; 无人物主体，建议突出产品/场景本身<br>' : '&#10004; 有人物出镜，建议注意构图（三分/居中）<br>'}
      </div>
    </div>
  `;
}

function renderShootingFinal() { renderShooting(analysisResult); }
'''

idx = content.find('// ── Init ──')
if idx > 0:
    content = content[:idx] + render_fn + '\n' + content[idx:]
    print('[3/4] Added renderShooting function')
else:
    print('[WARN] // ── Init ── not found, skipping function insert')

# 4. Call renderShooting in processFile (after renderReport)
old_call = '    renderReport(analysisResult, speechResult);\n    toast(`分析完成！类型: ${fullContentType.label} | 帧: ${frames.length}`);'
new_call = '    renderReport(analysisResult, speechResult);\n    renderShooting(analysisResult);\n    toast(`分析完成！类型: ${fullContentType.label} | 帧: ${frames.length}`);'
if old_call in content:
    content = content.replace(old_call, new_call, 1)
    print('[4/4] Added renderShooting call in processFile')
else:
    print('[WARN] renderReport call not found, trying alternative...')
    # Try to find it with different formatting
    if 'renderReport(analysisResult, speechResult)' in content:
        print('[INFO] Found renderReport call, but formatting differs')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('\nDone! Shooting tab added.')
