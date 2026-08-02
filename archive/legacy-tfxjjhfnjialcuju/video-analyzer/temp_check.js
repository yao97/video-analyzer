// State
let analysisResult = null;
let speechResult = null;
let frameImages = [];
let chartRefs = {};
let transcribeJobId = null;
let transcribePollTimer = null;

// Helpers
const $ = id => document.getElementById(id);
const show = id => $(id)?.classList.remove('hidden');
const hide = id => $(id)?.classList.add('hidden');

const toast = (msg, type='success') => {
  const t = $('toast');
  t.textContent = msg; t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 3500);
};

const switchTab = (btn, pid) => {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  $(pid)?.classList.add('active');
  if (pid === 'tabCharts') setTimeout(() => Object.values(chartRefs).forEach(c => c?.resize?.()), 80);
};

const COLOR_RGB = {
  '红色':'#f87171','橙色':'#fb923c','黄色':'#fbbf24','绿色':'#4ade80',
  '青色':'#22d3ee','蓝色':'#60a5fa','紫色':'#a78bfa','粉色':'#f472b6',
  '白色':'#f8fafc','灰色':'#94a3b8','黑色':'#374151',
};
const colorHex = n => COLOR_RGB[n] || '#94a3b8';

function setBadge(id, status, text) {
  const el = $(id);
  if (!el) return;
  el.className = 'badge ' + status;
  const t = $(id + 'Text');
  if (t) t.textContent = text;
}

function setStep(id, status, time) {
  const el = $(id);
  if (!el) return;
  el.className = 'step-icon ' + status;
  el.textContent = status === 'done' ? '✓' : (status === 'running' ? '●' : el.textContent.match(/\d/)?.[0] || '?');
  if (time !== undefined) {
    const stepEl = el.parentElement;
    const timeEl = stepEl.querySelector('.step-time');
    if (timeEl) timeEl.textContent = time;
  }
}

function updateWhisperProgress(progress, estimatedRemaining) {
  // 显示进度条容器
  show('whisperProgressWrap');
  // 更新百分比
  const pct = Math.round(Math.min(80, progress));
  $('whisperPct').textContent = pct + '%';
  $('whisperBar').style.width = pct + '%';
  // 更新预估剩余时间
  if (estimatedRemaining !== undefined && estimatedRemaining > 0) {
    $('whisperETASec').textContent = Math.round(estimatedRemaining);
    $('whisperETA').style.display = '';
  } else {
    $('whisperETASec').textContent = '--';
  }
  // 颜色随进度变化
  const hue = 220 + (pct / 80) * 60;
  $('whisperBar').style.background = `linear-gradient(90deg, hsl(${hue},70%,60%), hsl(${hue+20},70%,70%), hsl(${hue+40},70%,75%))`;
}

function hideWhisperProgress(finalPct) {
  // 完成时先显示 100% 再渐隐

  if (finalPct !== undefined) {
    $('whisperPct').textContent = '100%';
    $('whisperBar').style.width = '100%';
    $('whisperBar').style.transition = 'width 0.4s ease, opacity 0.6s ease 0.3s';
    $('whisperBar').style.opacity = '0';
    $('whisperETA').style.display = 'none';
    setTimeout(() => hide('whisperProgressWrap'), 1000);
  } else {
    hide('whisperProgressWrap');
  }
}

// ═══════════════════════════════════════════════════════════════
// Content Type Engine (基于画面多维特征)
// ═══════════════════════════════════════════════════════════════

// 特征权重矩阵：每个类型对每个特征的期望值范围
const CONTENT_TYPE_RULES = {
  ECOMMERCE: {
    weight: 1.0,
    signals: [
      { check: f => f.whiteRatio > 0.28, score: 3, reason: '白底/浅色背景（占比' }, // +
      { check: f => f.skinRatio < 0.08, score: 2, reason: '无人脸/皮肤区域' }, // +
      { check: f => f.textRatio > 2, score: 1.5, reason: '有字幕文字' }, // +
      { check: f => f.motion < 0.15, score: 1, reason: '画面稳定' }, // +
      { check: f => f.brightness > 0.6, score: 1, reason: '整体明亮' }, // +
      { check: f => f.darkRatio < 0.3, score: 0.5, reason: '非暗光场景' }, // -
      { check: f => f.blueRatio < 0.06, score: 0.5, reason: '无设备蓝色' }, // -
    ],
    tags: ['白底背景','单一主体','产品展示','字幕密集','稳定镜头'],
    desc: '以产品展示为核心，画面纯净，常见于抖音/小红书带货视频。',
  },
  VLOG: {
    weight: 1.0,
    signals: [
      { check: f => f.skinRatio > 0.1, score: 3, reason: '有人物/面部' }, // +
      { check: f => f.motion > 0.15, score: 2, reason: '镜头运动较多' }, // +
      { check: f => f.textRatio > 2.5, score: 1.5, reason: '有字幕叙事' }, // +
      { check: f => f.whiteRatio < 0.4, score: 1, reason: '非纯白底' }, // +
      { check: f => f.brightness > 0.3 && f.brightness < 0.75, score: 1, reason: '自然光环境' }, // +
      { check: f => f.blueRatio < 0.1, score: 0.5, reason: '无设备界面' }, // -
    ],
    tags: ['人物出镜','生活场景','运动镜头','字幕叙事'],
    desc: '真人出镜为主，记录生活、分享观点或经历。',
  },
  MEDICAL: {
    weight: 1.0,
    signals: [
      { check: f => f.blueRatio > 0.03, score: 3, reason: '有蓝色元素（设备/屏幕）' }, // +
      { check: f => f.skinRatio > 0.08, score: 2.5, reason: '有皮肤/治疗画面' }, // +
      { check: f => f.textRatio > 2, score: 1.5, reason: '有字幕/说明文字' }, // +
      { check: f => f.rednessRatio > 0.03, score: 1.5, reason: '有红/暖色（治疗效果）' }, // +
      { check: f => f.whiteRatio > 0.15 && f.whiteRatio < 0.5, score: 1, reason: '诊所/医疗环境' }, // +
      { check: f => f.skinRatio < 0.05 && f.blueRatio < 0.03, score: -3, reason: '既无皮肤也无设备' }, // -
      { check: f => f.whiteRatio > 0.4 && f.skinRatio < 0.05, score: -2, reason: '纯白底产品图' }, // -
    ],
    tags: ['设备界面','皮肤特写','治疗画面','诊所环境'],
    desc: '医美/医疗项目讲解，包含设备介绍、治疗过程或医学科普。',
  },
  FOOD: {
    weight: 1.0,
    signals: [
      { check: f => f.hue > 5 && f.hue < 55, score: 3, reason: '暖色调（红/橙/黄）' }, // +
      { check: f => f.sat > 80, score: 2, reason: '高饱和度（食物色泽）' }, // +
      { check: f => f.brightness > 0.3 && f.brightness < 0.75, score: 1.5, reason: '暖光/自然光' }, // +
      { check: f => f.whiteRatio > 0.2, score: 1, reason: '餐具/餐具白' }, // +
      { check: f => f.rednessRatio > 0.05, score: 1, reason: '红色食物元素' }, // +
      { check: f => f.skinRatio > 0.1, score: 0.5, reason: '手部/人物入镜' }, // +
      { check: f => f.blueRatio > 0.1, score: -1, reason: '蓝色背景/非食物' }, // -
    ],
    tags: ['暖色调','高饱和','美食特写','餐具'],
    desc: '美食制作或品尝，展示食物色泽和诱人细节。',
  },
  EDUCATION: {
    weight: 1.0,
    signals: [
      { check: f => f.textRatio > 4, score: 3.5, reason: '高文字密度' }, // +++
      { check: f => f.blueRatio > 0.02, score: 2, reason: '屏幕/PPT蓝色' }, // +
      { check: f => f.brightness > 0.5, score: 1.5, reason: '明亮教学环境' }, // +
      { check: f => f.skinRatio > 0.05, score: 1, reason: '讲师出镜' }, // +
      { check: f => f.motion < 0.3, score: 1, reason: '镜头相对稳定' }, // +
      { check: f => f.whiteRatio > 0.2, score: 0.5, reason: '白板/背景' }, // +
      { check: f => f.skinRatio > 0.2 && f.textRatio < 2, score: -2, reason: '人物特写+无文字' }, // -
    ],
    tags: ['高文字密度','屏幕内容','讲师出镜','结构化讲解'],
    desc: '传授知识或技能，文字信息量大，逻辑清晰。',
  },
  VIDEO_EDIT: {
    weight: 1.0,
    signals: [
      { check: f => f.brightness < 0.45, score: 2.5, reason: '暗光/电影感色调' }, // +
      { check: f => f.motion > 0.25, score: 2, reason: '镜头运动丰富' }, // +
      { check: f => f.whiteRatio < 0.2, score: 1.5, reason: '深色背景' }, // +
      { check: f => f.textRatio > 2, score: 1.5, reason: '有字幕翻译' }, // +
      { check: f => f.darkRatio > 0.25, score: 1, reason: '大面积暗部' }, // +
      { check: f => f.blueRatio > 0.05, score: 0.5, reason: '蓝色调/夜景' }, // +
      { check: f => f.brightness > 0.65, score: -1, reason: '过于明亮非电影感' }, // -
    ],
    tags: ['暗光色调','多场景','快速切换','电影感'],
    desc: '影视剪辑或情景短剧，有明显叙事结构和镜头语言。',
  },
  LIVE_COMMERCE: {
    weight: 1.0,
    signals: [
      { check: f => f.textRatio > 5, score: 3, reason: '极高文字密度（价格/信息）' }, // +++
      { check: f => f.skinRatio > 0.08, score: 2, reason: '主播出镜' }, // +
      { check: f => f.whiteRatio > 0.25, score: 1.5, reason: '商品白底' }, // +
      { check: f => f.brightness > 0.55, score: 1, reason: '直播间明亮' }, // +
      { check: f => f.motion > 0.15, score: 1, reason: '现场感强' }, // +
      { check: f => f.sat > 100, score: 1, reason: '色彩鲜艳' }, // +
      { check: f => f.skinRatio < 0.05 && f.textRatio < 3, score: -2, reason: '无人物+无密集文字' }, // -
    ],
    tags: ['价格标注','商品展示','主播出镜','高信息密度'],
    desc: '直播间录制，内容紧凑，节奏快，信息密度高。',
  },
  ANIMATION: {
    weight: 0.8,
    signals: [
      { check: f => f.brightness > 0.5 && f.brightness < 0.8, score: 1.5, reason: '卡通化亮度' }, // +
      { check: f => f.sat > 80, score: 2, reason: '高饱和色彩' }, // +
      { check: f => f.skinRatio < 0.05, score: 1.5, reason: '无真实皮肤' }, // +
      { check: f => f.textRatio < 2, score: 1, reason: '无密集文字' }, // +
      { check: f => f.blueRatio > 0.03 || f.purpleRatio > 0.03, score: 1, reason: '蓝紫/动漫色调' }, // +
    ],
    tags: ['动漫风格','高饱和','非真实人像'],
    desc: '动画/CG内容，色彩饱和，画面风格化。',
  },
  SCREEN_RECORD: {
    weight: 0.8,
    signals: [
      { check: f => f.blueRatio > 0.05, score: 2.5, reason: '蓝色屏幕界面' }, // +
      { check: f => f.textRatio > 3, score: 2, reason: '屏幕文字密集' }, // +
      { check: f => f.whiteRatio > 0.2, score: 1.5, reason: '软件界面白底' }, // +
      { check: f => f.skinRatio < 0.05, score: 1.5, reason: '无人物' }, // +

      { check: f => f.motion < 0.15, score: 1, reason: '屏幕内容相对静止' }, // +
      { check: f => f.sat < 60, score: 0.5, reason: '低饱和（屏幕色彩）' }, // +
      { check: f => f.skinRatio > 0.1, score: -2, reason: '有人物画面' }, // -
    ],
    tags: ['录屏界面','软件演示','蓝色UI','高文字'],
    desc: '屏幕录制，包含软件演示、教程、游戏录屏等。',
  },
  GENERAL: {
    weight: 0.3,
    signals: [
      { check: () => true, score: 0.5, reason: '无法归入其他类型' },
    ],
    tags: [],
    desc: '通用视频，未能明确归入特定类型。',
  },
};

function scoreContentType(frames) {
  const scores = {};
  for (const [typeId, typeDef] of Object.entries(CONTENT_TYPE_RULES)) {
    let totalScore = 0;
    let matchedSignals = [];
    let failedSignals = [];

    for (const signal of typeDef.signals) {
      // 取各帧的平均值来评估
      const vals = frames.map(f => {
        try { return signal.check(f); } catch { return false; }
      });
      const passCount = vals.filter(Boolean).length;
      const passRate = passCount / frames.length;

      if (passRate > 0.3) {
        totalScore += signal.score * passRate;
        matchedSignals.push({ reason: signal.reason, score: signal.score, passRate });
      } else if (signal.score < 0) {
        totalScore += signal.score;

        failedSignals.push(signal.reason);
      }
    }

    scores[typeId] = {
      typeId,
      score: totalScore * typeDef.weight,
      matchedSignals,
      failedSignals,
    };
  }


  // 排序
  const sorted = Object.values(scores).sort((a, b) => b.score - a.score);
  return sorted;
}

function detectContentType(frames) {
  if (!frames.length) return { ...CONTENT_TYPE_RULES.GENERAL, id: 'GENERAL' };
  const scored = scoreContentType(frames);
  const top = scored[0];
  const typeDef = CONTENT_TYPE_RULES[top.typeId];
  return { ...typeDef, id: top.typeId, _score: top };
}

// ═══════════════════════════════════════════════════════════════
// Color Analysis (Canvas)
// ═══════════════════════════════════════════════════════════════
async function analyzeFramesColor(imgSrcs) {
  const results = [];
  for (let i = 0; i < imgSrcs.length; i++) {
    const img = new Image();
    await new Promise(res => { img.onload = res; img.src = imgSrcs[i]; });
    const canvas = document.createElement('canvas');
    canvas.width = 120;
    canvas.height = Math.round(120 * img.height / img.width);
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;

    let rS=0, gS=0, bS=0;
    let skinP=0, redP=0, whiteP=0, blueP=0, darkP=0, textP=0, purpleP=0;
    const cc = {};
    let total = data.length / 4;

    for (let j = 0; j < data.length; j += 4) {
      const r = data[j], g = data[j+1], b = data[j+2];
      rS += r; gS += g; bS += b;

      // Skin detection (classic)
      if (r > 80 && g > 55 && b > 40 && r > g && r > b && Math.abs(r-g) < 65 && r > 95) skinP++;

      // Red/orange
      if (r > 150 && r > g * 1.3 && r > b * 1.3) redP++;

      // White background
      if (r > 215 && g > 215 && b > 215 && Math.abs(r-g) < 35) whiteP++;

      // Blue (device UI / sky / water)
      if (b > 110 && b > r * 1.15 && b > g * 1.1) blueP++;

      // Purple
      if (r > 100 && b > 120 && r < b && g < 100) purpleP++;

      // Dark
      if (r < 55 && g < 55 && b < 55) darkP++;

      // Text (high contrast)
      const rng = Math.max(r,g,b) - Math.min(r,g,b);
      if (rng > 180 && (r > 200 || g > 200 || b > 200) && (r < 60 || g < 60 || b < 60)) textP++;

      // HSV color classification
      const maxC = Math.max(r,g,b), minC = Math.min(r,g,b);
      const delta = maxC - minC;
      let name;
      if (delta < 15) name = maxC > 200 ? '白色' : '灰色';
      else {
        let hDeg;
        if (maxC === r) hDeg = 60 * ((g-b)/delta % 6);
        else if (maxC === g) hDeg = 60 * ((b-r)/delta + 2);
        else hDeg = 60 * ((r-g)/delta + 4);
        hDeg = (hDeg + 360) % 360;
        if (hDeg < 15 || hDeg >= 345) name = '红色';
        else if (hDeg < 40) name = '橙色';
        else if (hDeg < 75) name = '黄色';
        else if (hDeg < 155) name = '绿色';
        else if (hDeg < 210) name = '青色';
        else if (hDeg < 265) name = '蓝色';
        else if (hDeg < 295) name = '紫色';
        else name = '粉色';
      }
      cc[name] = (cc[name] || 0) + 1;
    }

    const avgR = rS/total, avgG = gS/total, avgB = bS/total;
    const brightness = (avgR*0.299 + avgG*0.587 + avgB*0.114) / 255;
    const maxC2 = Math.max(avgR, avgG, avgB), minC2 = Math.min(avgR, avgG, avgB);
    const satV = maxC2 === 0 ? 0 : (maxC2 - minC2) / maxC2 * 255;
    let hueV = 0;
    if (maxC2 === avgR) hueV = 60 * ((avgG-avgB)/((maxC2-minC2)||1) % 6);
    else if (maxC2 === avgG) hueV = 60 * ((avgB-avgR)/(maxC2-minC2||1) + 2);
    else hueV = 60 * ((avgR-avgG)/(maxC2-minC2||1) + 4);
    hueV = (hueV + 360) % 360;

    const topColors = Object.entries(cc).sort((a,b) => b[1]-a[1]).slice(0,5).map(e => e[0]);

    // Shot type estimation
    let shotType = 'UNKNOWN';
    if (skinP/total > 0.15) shotType = '人物特写';
    else if (skinP/total > 0.05) shotType = '人物中景';
    else if (whiteP/total > 0.3) shotType = '产品展示';
    else if (darkP/total > 0.25) shotType = '暗光场景';
    else if (blueP/total > 0.05) shotType = '蓝色场景';
    else shotType = '一般场景';

    results.push({
      t: 0,
      brightness: +brightness.toFixed(3),
      hue: +hueV.toFixed(1),
      sat: +satV.toFixed(1),
      motion: 0, motionLabel: '静止',
      brightnessLabel: brightness > 0.65 ? '明亮' : (brightness < 0.3 ? '昏暗' : '适中'),
      skinRatio: +(skinP/total).toFixed(3),
      rednessRatio: +(redP/total).toFixed(3),
      whiteRatio: +(whiteP/total).toFixed(3),
      blueRatio: +(blueP/total).toFixed(3),
      purpleRatio: +(purpleP/total).toFixed(3),
      darkRatio: +(darkP/total).toFixed(3),
      textRatio: +(textP/total*100).toFixed(2),
      hasText: textP/total > 0.008,
      colors: topColors,
      dominantColor: topColors[0] || '灰色',

      avgR: +avgR.toFixed(1), avgG: +avgG.toFixed(1), avgB: +avgB.toFixed(1),
      shotType,
    });
  }

  results.forEach((r, i) => r.t = frameImages[i].t);

  for (let i = 1; i < results.length; i++) {
    const dB = Math.abs(results[i].brightness - results[i-1].brightness) * 2
             + Math.abs(results[i].skinRatio - results[i-1].skinRatio);
    const m = Math.min(1, dB * 3);
    results[i].motion = m;

    results[i].motionLabel = m < 0.05 ? '低' : (m < 0.2 ? '中' : '高');
  }
  return results;
}

function findSceneChanges(frames) {
  const changes = [];
  for (let i = 1; i < frames.length; i++) {
    const dB = Math.abs(frames[i].brightness - frames[i-1].brightness);
    const dS = Math.abs(frames[i].skinRatio - frames[i-1].skinRatio);
    const dC = frames[i].dominantColor !== frames[i-1].dominantColor ? 1 : 0;
    const score = (dB * 2 + dS * 0.5 + dC) * 50;
    if (score > 8) changes.push({ t: frames[i].t, score: +score.toFixed(0) });
  }
  return changes;
}

function buildPhases(frames, contentType) {
  const phases = []; let current = null;
  for (const f of frames) {
    // Use content type's phase logic if available

  const segs = speechResult.segments;
  const phases = contentType?.copyStructure || [{phase:'OPEN',label:'开场'},{phase:'BODY',label:'主体'},{phase:'END',label:'结尾'}];
  const phaseLen = duration / phases.length;
  const lines = [];
  for (let i = 0; i < phases.length; i++) {
    const p = phases[i];
    const start = i * phaseLen;
    const end = (i+1) * phaseLen;
    const segText = segs.filter(s => s.start >= start && s.start < end).map(s => s.text).join(' ');
    lines.push(`【${p.label}】${segText || '(该时段无语音内容)'}`);
  }
  return lines.join('\n');
}

// ═══════════════════════════════════════════════════════════════
// Phase Logic per Content Type
// ═══════════════════════════════════════════════════════════════
function getPhaseLogic(typeId) {
  const logics = {
    MEDICAL: (f) => {
      if (f.blueRatio > 0.04) return {name:'DEVICE',label:'设备界面',color:'#60a5fa'};
      if (f.skinRatio > 0.12) return {name:'TREATMENT',label:'治疗画面',color:'#6ee7b7'};
      if (f.textRatio > 4) return {name:'EXPLAIN',label:'字幕讲解',color:'#fbbf24'};
      if (f.whiteRatio > 0.25) return {name:'CLINIC',label:'诊所环境',color:'#fcd34d'};
      return {name:'TRANSITION',label:'转场',color:'#94a3b8'};
    },
    ECOMMERCE: (f) => {
      if (f.whiteRatio > 0.28) return {name:'PRODUCT',label:'产品展示',color:'#f87171'};
      if (f.textRatio > 5 && f.brightness > 0.5) return {name:'TEXT_INTRO',label:'文字开场',color:'#fbbf24'};
      if (f.motion > 0.2) return {name:'DEMO',label:'演示环节',color:'#4ade80'};
      return {name:'TRANSITION',label:'转场',color:'#94a3b8'};
    },
    VLOG: (f) => {
      if (f.skinRatio > 0.15) return {name:'FACE',label:'人物出镜',color:'#f472b6'};
      if (f.textRatio > 4) return {name:'TEXT_NAR',label:'字幕叙事',color:'#fbbf24'};
      if (f.motion > 0.25) return {name:'ACTION',label:'动态场景',color:'#4ade80'};
      return {name:'SCENE',label:'场景',color:'#94a3b8'};
    },
    FOOD: (f) => {
      if (f.hue > 5 && f.hue < 55 && f.sat > 80) return {name:'FOOD',label:'美食特写',color:'#fb923c'};
      if (f.brightness < 0.5) return {name:'COOKING',label:'烹饪过程',color:'#f87171'};
      if (f.whiteRatio > 0.25) return {name:'INGREDIENT',label:'餐具/食材',color:'#f8fafc'};
      return {name:'TRANSITION',label:'转场',color:'#94a3b8'};
    },
    EDUCATION: (f) => {
      if (f.textRatio > 5) return {name:'TEXT_LESSON',label:'文字讲解',color:'#a78bfa'};
      if (f.skinRatio > 0.1) return {name:'TEACHER',label:'讲师出镜',color:'#f472b6'};
      if (f.blueRatio > 0.03) return {name:'SCREEN',label:'屏幕内容',color:'#60a5fa'};
      return {name:'DIAGRAM',label:'图表演示',color:'#4ade80'};
    },
    VIDEO_EDIT: (f) => {
      if (f.brightness < 0.4) return {name:'DARK',label:'暗光场景',color:'#6366f1'};
      if (f.motion > 0.25) return {name:'ACTION',label:'动作场景',color:'#f87171'};
      if (f.textRatio > 3) return {name:'SUBTITLE',label:'字幕',color:'#fbbf24'};
      return {name:'NARRATIVE',label:'叙事',color:'#94a3b8'};
    },
    LIVE_COMMERCE: (f) => {
      if (f.textRatio > 5) return {name:'PRICE_TAG',label:'价格标注',color:'#ef4444'};
      if (f.skinRatio > 0.1) return {name:'HOST',label:'主播出镜',color:'#f472b6'};
      if (f.whiteRatio > 0.25) return {name:'PRODUCT',label:'商品展示',color:'#f87171'};
      return {name:'LIVE',label:'直播现场',color:'#ef4444'};
    },
    SCREEN_RECORD: (f) => {
      if (f.blueRatio > 0.05) return {name:'INTERFACE',label:'软件界面',color:'#60a5fa'};

      if (f.textRatio > 4) return {name:'TEXT_CONTENT',label:'文字内容',color:'#a78bfa'};
      return {name:'SCREEN',label:'屏幕',color:'#94a3b8'};
    },
    ANIMATION: (f) => {
      if (f.sat > 100) return {name:'CARTOON',label:'动画画面',color:'#a78bfa'};
      if (f.blueRatio > 0.03 || f.purpleRatio > 0.03) return {name:'BLUE_PURPLE',label:'蓝紫调',color:'#6366f1'};
      return {name:'ANIM_SCENE',label:'动画场景',color:'#94a3b8'};
    },
    GENERAL: (f) => {
      if (f.textRatio > 4) return {name:'TEXT',label:'文字',color:'#fbbf24'};
      if (f.skinRatio > 0.1) return {name:'PERSON',label:'人物',color:'#f472b6'};
      return {name:'SCENE',label:'一般场景',color:'#94a3b8'};
    },
  };
  return logics[typeId] || logics.GENERAL;
}

const CONTENT_TYPES_WITH_META = Object.fromEntries(
  Object.entries(CONTENT_TYPE_RULES).map(([id, def]) => [
    id,
    { ...def, id, phaseLogic: getPhaseLogic(id) }
  ])
);

// ═══════════════════════════════════════════════════════════════
// Main Pipeline
// ═══════════════════════════════════════════════════════════════
async function processFile(file) {
  if (!file.type.startsWith('video/')) { toast('请上传视频文件', 'error'); return; }
  if (file.size > 600*1024*1024) { toast('文件过大（>600MB）', 'error'); return; }

  // Reset state
  speechResult = null;
  transcribeJobId = null;
  clearInterval(transcribePollTimer);

  show('spinner');
  $('spinnerText').textContent = '读取视频...';
  $('spinnerSub').textContent = '准备中';
  $('spinnerFill').style.width = '5%';

  setBadge('badgeColor','running','分析中');
  setBadge('badgeSpeech','wait','等待');
  setBadge('badgeContent','wait','等待');
  setBadge('badgeCopy','wait','等待');

  // Reset step indicators
  ['stepUpload','stepExtract','stepWhisper','stepDone'].forEach((id,i) => setStep(id,'wait'));

  try {
    // ── 1. 加载视频 ──
    const video = document.createElement('video');
    video.preload = 'metadata';
    video.muted = false;
    video.src = URL.createObjectURL(file);
    await new Promise((res,rej) => { video.onloadedmetadata = res; video.onerror = rej; });

    // 显示视频预览（左侧面板）
    $('videoPreview').style.display = 'block';
    $('videoPreview').src = video.src;
    $('previewMeta').innerHTML =
      `分辨率: ${video.videoWidth}x${video.videoHeight} &nbsp;|&nbsp; 时长: ${video.duration.toFixed(1)}s<br>` +
      `文件大小: ${(file.size/1024/1024).toFixed(2)} MB &nbsp;|&nbsp; 类型: ${file.type}`;
    document.body.classList.add('video-active');
    $('mainLayout').style.display = 'flex';
    // 隐藏顶部的上传提示（如果有）
    document.querySelectorAll('.upload-zone').forEach(z => z.style.display = 'none');

    const duration = video.duration;
    const vw = video.videoWidth;
    const vh = video.videoHeight;
    const fps = 30;
    const totalFrames = Math.floor(duration * fps);

    $('spinnerFill').style.width = '10%';
    $('spinnerSub').textContent = '提取关键帧...';

    // ── 2. 提取帧 ──
    const numFrames = Math.min(15, Math.max(6, Math.floor(duration / 3)));
    frameImages = [];
    const tmpCanvas = document.createElement('canvas');
    tmpCanvas.width = vw; tmpCanvas.height = vh;
    const tCtx = tmpCanvas.getContext('2d');

    for (let i = 0; i < numFrames; i++) {
      const t = (i / numFrames) * duration * 0.97 + duration * 0.015;
      await new Promise(resolve => {
        video.currentTime = Math.min(t, duration - 0.01);
        video.onseeked = () => {
          tCtx.drawImage(video, 0, 0);
          tmpCanvas.toBlob(blob => {
            if (blob) frameImages.push({ blob, img: URL.createObjectURL(blob), t: +(video.currentTime).toFixed(1) });
            resolve();
          }, 'image/jpeg', 0.82);
        };
      });
      $('spinnerFill').style.width = (10 + 20 * (i/numFrames)) + '%';
      $('spinnerSub').textContent = `提取帧 ${i+1}/${numFrames}...`;
    }

    frameImages.sort((a,b) => a.t - b.t);
    frameImages = frameImages.reduce((acc, f) => {
      if (!acc.find(a => Math.abs(a.t-f.t) < 0.3)) acc.push(f);
      return acc;
    }, []);

    // ── 3. 色彩分析 ──
    $('spinnerSub').textContent = '分析画面色彩...';
    $('spinnerFill').style.width = '35%';
    const frames = await analyzeFramesColor(frameImages.map(f => f.img));
    $('spinnerFill').style.width = '45%';

    // ── 4. 内容类型识别 ──
    $('spinnerSub').textContent = '识别内容类型...';
    const contentType = detectContentType(frames);
    const typeDef = CONTENT_TYPES_WITH_META[contentType.id] || CONTENT_TYPES_WITH_META.GENERAL;
    const fullContentType = { ...typeDef, id: contentType.id, _score: contentType._score };
    const sceneChanges = findSceneChanges(frames);
    const phases = buildPhases(frames, fullContentType);

    analysisResult = {
      name: file.name, duration, fps, width: vw, height: vh,
      totalFrames, fileSize: (file.size/1024/1024).toFixed(2),
      frames, contentType: fullContentType, sceneChanges, phases,
    };

    setBadge('badgeColor','ok', frames.length+'帧');
    setBadge('badgeContent','ok', fullContentType.label);
    $('spinnerFill').style.width = '50%';
    $('spinnerSub').textContent = '画面分析完成 ✓';

    // ── 5. 渲染画面分析结果（立即显示）──
    renderMetrics(analysisResult);
    renderOverview(analysisResult);
    renderFrames(analysisResult);
    renderCharts(analysisResult);
    renderStructure(analysisResult);

    show('featureBadges');
    show('metricsSection');
    show('tabsSection');
    hide('spinner');

    // ── 6. 启动语音转写（后台）──
    $('spinnerSub').textContent = '启动语音转写...';
    setBadge('badgeSpeech','running','启动中');
    setStep('stepUpload','running');
    hideWhisperProgress();

    const jobId = await startTranscription(file, duration);
    if (jobId) {
      transcribeJobId = jobId;
      setStep('stepUpload','done','完成');
      setBadge('badgeSpeech','running','转写中');
      updateWhisperProgress(40, null);  // 显示进度条，每 2s 轮询更新

      // Poll every 2s
      transcribePollTimer = setInterval(() => pollTranscribeResult(jobId), 2000);
      // Also start immediately
      pollTranscribeResult(jobId);
    } else {
      // Backend unavailable
      setBadge('badgeSpeech','fail','服务未启动');
      setStep('stepUpload','fail');
      $('speechTimeline').innerHTML = `<div style="color:var(--yellow);font-size:0.8rem;padding:1rem 0;">
        &#9888; 转写服务未启动。请先运行以下命令启动服务：br>`
`
        );
    }

    const phaseLogic = contentType.phaseLogic || ((f) => ({ name: 'SCENE', label: '场景', color: '#94a3b8' }));
    const p = phaseLogic(f);
    if (!current || current.name !== p.name) {
      if (current) phases.push(current);
      current = { ...p, start: f.t, end: f.t, frames: [f] };
    } else {
      current.end = f.t;
      current.frames.push(f);
    }
  }
  if (current) phases.push(current);
  return phases;
}

// ═══════════════════════════════════════════════════════════════
// Transcribe API
// ═══════════════════════════════════════════════════════════════
async function startTranscription(file, duration) {
  const formData = new FormData();

  formData.append('video', file);
  formData.append('duration', String(duration));

  try {
    const resp = await fetch('http://192.168.0.8:8766/api/transcribe', {
      method: 'POST',
      body: formData,
    });
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    return data.job_id;
  } catch(e) {
    console.error('Transcribe start failed:', e);
    return null;
  }
}

async function pollTranscribeResult(jobId) {
  try {
    // Status
    const statusResp = await fetch(`http://192.168.0.8:8766/api/status/${jobId}`);
    const statusData = await statusResp.json();

    // Update step indicators
    setStep('stepUpload', 'done', '完成');
    if (statusData.status === 'extracting' || statusData.status === 'starting') {
      setStep('stepExtract', 'running');
      setStep('stepWhisper', 'wait');
      setStep('stepDone', 'wait');
    } else if (statusData.status === 'transcribing') {
      setStep('stepExtract', 'done', '完成');
      setStep('stepWhisper', 'running');
      setStep('stepDone', 'wait');
      // Whisper 进度条实时更新
      updateWhisperProgress(statusData.progress || 40, statusData.estimated_remaining);
    } else if (statusData.status === 'analyzing') {
      setStep('stepExtract', 'done', '完成');
      setStep('stepWhisper', 'done', '完成');
      setStep('stepDone', 'running');
    } else if (statusData.status === 'done') {
      setStep('stepExtract', 'done', '完成');
      setStep('stepWhisper', 'done', '完成');
      setStep('stepDone', 'done', '完成');
      clearInterval(transcribePollTimer);
      // Fetch result
      const resultResp = await fetch(`http://192.168.0.8:8766/api/result/${jobId}`);
      const resultData = await resultResp.json();
      if (resultData.result) {
        speechResult = resultData.result;
        setBadge('badgeSpeech', 'ok', (speechResult.segments?.length || 0) + '段');
        hideWhisperProgress(100);
        renderSpeech(speechResult, analysisResult?.contentType, analysisResult?.duration);
        renderOverviewFinal();
        renderStructureFinal();
        renderReportFinal();
        toast('语音转写完成！识别 ' + (speechResult.segments?.length || 0) + ' 段');
      }
      return;
    } else if (statusData.status === 'error') {
      setBadge('badgeSpeech', 'fail', '失败');
      setStep('stepWhisper', 'fail');
      clearInterval(transcribePollTimer);
      hideWhisperProgress();
      $('speechTimeline').innerHTML = `<div style="color:var(--red);font-size:0.8rem;padding:1rem 0;">转写失败: ${statusData.error || '未知错误'}（可能是静音视频或音频格式不支持）</div>`;
      return;
    } else if (statusData.status === 'no_audio') {
      setBadge('badgeSpeech', 'fail', '无音频');
      setStep('stepExtract', 'fail');
      clearInterval(transcribePollTimer);
      hideWhisperProgress();
      $('speechTimeline').innerHTML = `<div style="color:var(--yellow);font-size:0.8rem;padding:1rem 0;">未检测到音频轨道（该视频可能为静音视频）</div>`;
      return;
    }
  } catch(e) {
    console.error('Poll error:', e);
  }
}

// ═══════════════════════════════════════════════════════════════
// Keywords
// ═══════════════════════════════════════════════════════════════
function extractKeywords(text) {

  const ACTION_WORDS = new Set(['推荐','介绍','讲解','分享','展示','演示','告诉','帮助','发现','觉得','看到','注意','开始','使用','体验','感受','操作','完成','点击','打开','购买','点击','告诉您','告诉你们','怎么','如何','为什么','因为','所以','这样','那样']);
  const EMOTION_WORDS = new Set(['非常','特别','真的','简直','太','好','很','超','极','十分','喜欢','爱','赞','棒','厉害','牛','优秀','完美','漂亮','好看','开心','快乐','激动','兴奋','惊喜','满意','放心','绝绝子','太棒','超级','非常']);
  const STOP = new Set(['的是','这个','那个','就是','可以','没有','什么','怎么','一个','如果','因为','所以','而且','但是','或者','以及','还有','对于','关于','通过','进行']);

  const freq = {};
  const words = text.match(/[\u4e00-\u9fa5]{2,}/g) || [];
  words.forEach(w => freq[w] = (freq[w]||0) + 1);
  const sorted = Object.entries(freq).sort((a,b) => b[1]-a[1]);

  const highFreq = sorted.filter(([w]) => w.length>=2 && !STOP.has(w) && freq[w]>=2).slice(0,20).map(e=>e[0]);
  const actions = sorted.filter(([w]) => ACTION_WORDS.has(w)).slice(0,10).map(e=>e[0]);
  const emotions = sorted.filter(([w]) => EMOTION_WORDS.has(w) || [...EMOTION_WORDS].some(e=>w.includes(e))).slice(0,10).map(e=>e[0]);
  const products = sorted.filter(([w]) => w.length>=3 && freq[w]>=1 && !STOP.has(w)).slice(0,15).map(e=>e[0]);

  return { highFreq, actions, emotions, products };
}

function generateScript(speechResult, contentType, duration) {
  if (!speechResult?.segments?.length) return null;

          python transcribe_server.py --port 8766
        </code>
      </div>`;
    }

    toast(`分析完成！类型: ${fullContentType.label} | 帧: ${frames.length}`);

  } catch(err) {
    console.error(err);
    hide('spinner');
    toast('分析失败: ' + err.message, 'error');

  }
}

// ═══════════════════════════════════════════════════════════════
// Render Functions
// ═══════════════════════════════════════════════════════════════
function renderMetrics(r) {
  $('mDuration').textContent = r.duration.toFixed(1)+'s';
  $('mOrientation').textContent = r.height>r.width?'竖屏 9:16':'横屏 16:9';
  $('mResolution').textContent = r.width+'x'+r.height;
  $('mFps').textContent = r.fps;
  $('mFrames').textContent = r.totalFrames.toLocaleString();
  $('mSize').textContent = r.fileSize;
  $('mAudio').textContent = '?';
  $('mAudioSub').textContent = speechResult ? '已识别' : '检测中';
}

function renderOverview(r) {
  const ct = r.contentType;
  const score = ct._score;

  $('typeTitle').textContent = (ct.icon||'&#127909;').replace(/&#(\d+);/g,(_,c)=>'\\u'+c.padStart(4,'0')) + ' ' + ct.label;
  $('typeTitle').style.color = ct.color || 'var(--accent2)';
  $('typeText').textContent = ct.desc || '';
  $('contentSignals').innerHTML = (ct.tags||[]).map(t => `<span class="copy-tag">${t}</span>`).join('');

  // Show evidence
  if (score?.matchedSignals?.length) {
    const topSignals = score.matchedSignals.slice(0,5);
    $('contentEvidence').innerHTML = '匹配特征: ' + topSignals.map(s => `+${s.reason}${s.passRate>0.5?'(强)':''}`).join(' &nbsp;|&nbsp; ');
  }

  // Overview bars
  const frames = r.frames;
  const avgB = frames.reduce((s,f)=>s+f.brightness,0)/frames.length;
  const avgM = frames.reduce((s,f)=>s+f.motion,0)/frames.length;
  const avgT = frames.reduce((s,f)=>s+parseFloat(f.textRatio),0)/frames.length;
  $('overviewBars').innerHTML = `
    <div class="progress-label"><span>亮度</span><span>${(avgB*100).toFixed(0)}%</span></div>
    <div class="progress-bar"><div class="progress-fill" style="background:#fbbf24;width:${(avgB*100).toFixed(0)}%"></div></div>
    <div class="progress-label"><span>运动度</span><span>${(avgM*100).toFixed(0)}%</span></div>
    <div class="progress-bar"><div class="progress-fill" style="background:#a78bfa;width:${(avgM*200).toFixed(0)}%"></div></div>
    <div class="progress-label"><span>文字密度</span><span>${avgT.toFixed(1)}%</span></div>
    <div class="progress-bar"><div class="progress-fill" style="background:#4ade80;width:${Math.min(100,(avgT*20)).toFixed(0)}%"></div></div>
    <div class="progress-label"><span>场景切换</span><span>${r.sceneChanges.length}处</span></div>
    <div class="progress-bar"><div class="progress-fill" style="background:#60a5fa;width:${Math.min(100,(r.sceneChanges.length*15)).toFixed(0)}%"></div></div>
  `;

function renderSpeechSummary() {
  $('speechSummaryCount').textContent = speechResult?.segments?.length ? `(${speechResult.segments.length}段)` : '';
  if (speechResult?.segments?.length) {
    $('speechSummaryBox').innerHTML = `<div class="speech-timeline">${speechResult.segments.slice(0,5).map(s =>
      `<div class="speech-segment"><span class="speech-time">@${s.start.toFixed(0)}s</span><span class="speech-text">${s.text}</span></div>`
    ).join('')}</div>`;
    if (speechResult.segments.length > 5) {
      $('speechSummaryBox').innerHTML += `<div style="color:var(--muted);font-size:0.73rem;margin-top:0.5rem;">...共 ${speechResult.segments.length} 段，切换到「语音转写」标签查看全部</div>`;
    }
  } else if (speechResult?.text) {
    $('speechSummaryBox').innerHTML = `<div class="speech-timeline"><div class="speech-segment"><span class="speech-text">${speechResult.text.slice(0,300)}${speechResult.text.length>300?'...':''}</span></div></div>`;
  } else {
    $('speechSummaryBox').innerHTML = `<div style="color:var(--muted);font-size:0.8rem;padding:0.5rem 0;">语音转写进行中或无音频...</div>`;
  }
}


function renderSpeech(speech, contentType, duration) {
  $('speechTabCount').textContent = speech?.segments?.length ? `(${speech.segments.length}段，${speech.text?.length||0}字)` : '';
  $('mAudioSub').textContent = '已识别';

  if (speech?.segments?.length) {
    $('speechTimeline').innerHTML = speech.segments.map(s => {
      // Highlight keywords
      const kw = speech.keywords;
      let text = s.text;
      if (kw?.highFreq) {
        kw.highFreq.forEach(word => {
          if (word.length >= 2) text = text.replace(new RegExp(word.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'), 'g'), `<span class="kw">${word}</span>`);
        });
      }
      if (kw?.actions) {
        kw.actions.forEach(word => {
          if (word.length >= 2) text = text.replace(new RegExp(word.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'), 'g'), `<span class="aw">${word}</span>`);
        });
      }
      return `<div class="speech-segment">
        <span class="speech-time">@${s.start.toFixed(0)}s</span>
        <span class="speech-text">${text}</span>
      </div>`;
    }).join('');

    // Keywords
    if (speech.keywords) {
      $('kwFreq').innerHTML = speech.keywords.highFreq.slice(0,12).map(k => `<span class="copy-tag">${k}</span>`).join('');
      $('kwAction').innerHTML = speech.keywords.actions.slice(0,8).map(k => `<span class="copy-tag yellow">${k}</span>`).join('');
      $('kwEmotion').innerHTML = speech.keywords.emotions.slice(0,8).map(k => `<span class="copy-tag purple">${k}</span>`).join('');
      $('kwProduct').innerHTML = speech.keywords.products.slice(0,12).map(k => `<span class="copy-tag green">${k}</span>`).join('');
    }
  } else if (speech?.text) {
    $('speechTimeline').innerHTML = `<div class="speech-segment"><span class="speech-text">${speech.text}</span></div>`;
  } else if (speech?.no_audio) {
    $('speechTimeline').innerHTML = `<div style="color:var(--muted);font-size:0.85rem;padding:1.2rem 0;">🎧 该视频无音轨（纯画面视频），无法转写语音。<br><span style="font-size:0.76rem;color:#999;">上传含声音的手机视频即可体验语音转写功能。</span></div>`;
    $('mAudioSub').textContent = '无音轨';
  } else {
    $('speechTimeline').innerHTML = `<div style="color:var(--muted);font-size:0.8rem;padding:1rem 0;">无语音内容</div>`;
  }

  // Generated script
  const script = generateScript(speech, contentType, duration);
  if (script) {
    $('generatedScript').textContent = script;
    setBadge('badgeCopy','ok','完成');
  } else {
    $('generatedScript').textContent = '（无语音内容，无法生成文案脚本）';
    setBadge('badgeCopy','ok','无语音');
  }
}


function renderOverviewFinal() { renderOverview(analysisResult); }
function renderStructureFinal() { renderStructure(analysisResult, true); }
function renderReportFinal() { renderReport(analysisResult, speechResult); }



function renderFrames(r) {
  $('frameCount').textContent = '('+r.frames.length+'帧)';
  const landscape = r.width > r.height;
  $('frameGrid').innerHTML = r.frames.map((f,i) =>
    `<div class="frame-card">
      <img src="${frameImages[i]?.img||''}" class="frame-img ${landscape?'landscape':''}" alt="frame">
      <div class="frame-body">
        <div class="frame-time">@${f.t}s</div>
        <div class="frame-tags">
          <span class="tag">${f.brightnessLabel}</span>
          <span class="tag">${f.motionLabel}动</span>
          ${f.hasText?'<span class="tag yellow">有文字</span>':''}
          ${f.skinRatio>0.1?'<span class="tag green">人物</span>':''}
          ${f.blueRatio>0.04?'<span class="tag blue">设备/蓝</span>':''}
          ${f.whiteRatio>0.25?'<span class="tag purple">白底</span>':''}
          ${f.rednessRatio>0.05?'<span class="tag red">红/暖</span>':''}
          ${f.darkRatio>0.25?'<span class="tag">暗光</span>':''}
          ${f.sat>100?'<span class="tag orange">高饱和</span>':''}
        </div>
        <div style="margin-top:0.3rem;font-size:0.65rem;color:var(--muted);">${f.shotType}</div>
      </div>
    </div>`
  ).join('');
}


function destroyCharts() {
  Object.values(chartRefs).forEach(c => { try { c.destroy(); } catch(e){} });
  chartRefs = {};
}


function renderCharts(r) {
  const frames = r.frames;
  const labels = frames.map(f => '@'+f.t+'s');
  if (!window.Chart) return;
  if (!$('chartRGB') || $('chartRGB').tagName !== 'CANVAS') return;

  destroyCharts();
  const opts = {
    responsive:true,
    plugins:{ legend:{ labels:{ color:'#8b8fa3', font:{ size:10 } } } },
    scales:{
      x:{ ticks:{ color:'#6b7084', font:{ size:9 } }, grid:{ color:'#2a2d3a' } },
      y:{ ticks:{ color:'#6b7084', font:{ size:10 } }, grid:{ color:'#2a2d3a' } },
    }
  };

  try {
    chartRefs['chartRGB'] = new Chart($('chartRGB'), {
      type:'line',
      data:{ labels, datasets:[
        {label:'R',data:frames.map(f=>+f.avgR),borderColor:'#f87171',tension:0.3},
        {label:'G',data:frames.map(f=>+f.avgG),borderColor:'#4ade80',tension:0.3},
        {label:'B',data:frames.map(f=>+f.avgB),borderColor:'#60a5fa',tension:0.3},
      ]},
      options:opts
    });
    chartRefs['chartBM'] = new Chart($('chartBM'), {
      type:'line',
      data:{ labels, datasets:[
        {label:'亮度',data:frames.map(f=>+f.brightness),borderColor:'#fbbf24',backgroundColor:'rgba(251,191,36,0.1)',fill:true,tension:0.3},
        {label:'运动',data:frames.map(f=>+f.motion),borderColor:'#a78bfa',borderDash:[4,2],tension:0.3},
        {label:'文字%',data:frames.map(f=>parseFloat(f.textRatio)/20),borderColor:'#4ade80',borderDash:[2,2],tension:0.3},
      ]},
      options:{...opts,scales:{...opts.scales,y1:{type:'linear',position:'right',...opts.scales.y}}}
    });
    chartRefs['chartText'] = new Chart($('chartText'), {
      type:'bar',
      data:{labels,datasets:[{label:'文字%',data:frames.map(f=>parseFloat(f.textRatio)),backgroundColor:'#a78bfa'}]},
      options:opts
    });
    const cc={};
    frames.forEach(f=>f.colors.slice(0,3).forEach(c=>cc[c]=(cc[c]||0)+1));
    const top6=Object.entries(cc).sort((a,b)=>b[1]-a[1]).slice(0,6);
    chartRefs['chartColorPie'] = new Chart($('chartColorPie'), {
      type:'doughnut',
      data:{labels:top6.map(e=>e[0]),datasets:[{data:top6.map(e=>e[1]),backgroundColor:top6.map(e=>colorHex(e[0]))}]},
      options:{plugins:{legend:{position:'right',labels:{color:'#8b8fa3',font:{size:10}}}}}
    });
  } catch(e) { console.warn('Charts failed', e); }

  $('frameTable').querySelector('tbody').innerHTML = frames.map(f =>
    `<tr><td>@${f.t}s</td><td>${f.colors.slice(0,3).join(',')}</td><td>${f.brightness.toFixed(2)}</td><td>${f.motionLabel}</td><td>${(f.skinRatio*100).toFixed(1)}%</td><td>${(f.blueRatio*100).toFixed(1)}%</td><td>${f.textRatio}%</td><td>${f.shotType}</td></tr>`
  ).join('');
}


function renderStructure(r, withSpeech = false) {
  const ct = r.contentType;
  $('structureNote').textContent = '（基于 '+ct.label+' 结构）';

  $('phaseList').innerHTML = r.phases.map(p => {
    const firstIdx = r.frames.indexOf(p.frames[0]);
    const thumb = frameImages[firstIdx]?.img || '';
    const avgSkin = p.frames.reduce((s,f)=>s+f.skinRatio,0)/p.frames.length*100;
    const avgText = p.frames.reduce((s,f)=>s+parseFloat(f.textRatio),0)/p.frames.length;
    const avgBlue = p.frames.reduce((s,f)=>s+f.blueRatio,0)/p.frames.length*100;
    const avgSat = p.frames.reduce((s,f)=>s+f.sat,0)/p.frames.length;
    const signals=[];
    if(avgSkin>10) signals.push('人物');
    if(avgBlue>4) signals.push('设备');
    if(avgText>4) signals.push('字幕');
    if(avgSat>100) signals.push('高饱和');
    if(p.frames[0]?.darkRatio>0.25) signals.push('暗光');

    const speechSeg = speechResult?.segments?.find(s => s.start>=p.start&&s.start<p.end);
    return `<div class="phase-item">
      <div class="phase-bar" style="background:${p.color}"></div>
      <div class="phase-body">
        <div class="phase-info">
          <div class="phase-name" style="color:${p.color}">${p.label}</div>
          <div class="phase-time">@${p.start.toFixed(0)}s - @${p.end.toFixed(0)}s (${(p.end-p.start).toFixed(1)}s)</div>
          <div class="phase-tags">${signals.map(s=>`<span class="tag">${s}</span>`).join('')}</div>
        </div>
        <div class="phase-desc">
          <div style="font-size:0.7rem;color:var(--muted);">
            皮肤:${avgSkin.toFixed(0)}% | 蓝:${avgBlue.toFixed(0)}% | 文字:${avgText.toFixed(1)}% | ${p.frames[0]?.shotType||''}
          </div>
          ${speechSeg ? `<div style="margin-top:0.25rem;font-size:0.72rem;color:var(--accent2);">"${speechSeg.text.slice(0,50)}${speechSeg.text.length>50?'...':''}"</div>` : ''}
        </div>
        ${thumb?`<img src="${thumb}" class="phase-thumb" style="object-fit:cover;" onerror="this.style.display='none'">`:''}
      </div>
    </div>`;
  }).join('');

  // Script table
  const phases = ct.copyStructure || [];
  $('scriptTable').querySelector('tbody').innerHTML = r.phases.map(p => {
    const match = phases.find(s => s.label.includes(p.label));
    const speechSeg = speechResult?.segments?.find(s => s.start>=p.start&&s.start<p.end);
    const avgB = p.frames.reduce((s,f)=>s+f.brightness,0)/p.frames.length;
    const visualDesc = avgB>0.65?'明亮':(avgB<0.3?'暗光':'适中');
    return `<tr>
      <td><span style="color:${p.color};font-weight:600;">${p.label}</span></td>
      <td>@${p.start.toFixed(0)}s-@${p.end.toFixed(0)}s</td>
      <td>${(p.end-p.start).toFixed(1)}s</td>
      <td>${visualDesc} · ${p.frames[0]?.shotType||'一般'}</td>
      <td>${speechSeg?speechSeg.text.slice(0,35)+'...':'(无语音)'}</td>
      <td>${match?match.template:'—'}</td>
    </tr>`;
  }).join('');
}

function renderReport(r, speech) {
  const now = new Date().toLocaleString('zh-CN');
  const ct = r.contentType;
  const avgB = (r.frames.reduce((s,f)=>s+f.brightness,0)/r.frames.length).toFixed(3);
  const avgM = (r.frames.reduce((s,f)=>s+f.motion,0)/r.frames.length).toFixed(3);
  const phaseLines = r.phases.map(p => `- **${p.label}** (@${p.start.toFixed(0)}s - @${p.end.toFixed(0)}s, ${(p.end-p.start).toFixed(1)}s)`).join('\n');
  const frameLines = r.frames.map(f => `| @${f.t}s | ${f.colors.slice(0,3).join(',')} | ${f.brightness.toFixed(2)} | ${f.motionLabel} | ${f.textRatio}% |`).join('\n');
  const speechLines = speech?.segments?.map(s => `| @${s.start.toFixed(1)}s | ${s.text} |`).join('\n') || '';
  const script = generateScript(speech, ct, r.duration);

  const md = `# 视频内容分析报告

**文件**: ${r.name}
**分析时间**: ${now}
**内容类型**: ${ct.label}
**分析帧数**: ${r.frames.length} 帧

---

## 一、基本信息

| 属性 | 数值 |
|------|------|
| 时长 | ${r.duration.toFixed(1)} 秒 |
| 分辨率 | ${r.width} x ${r.height} |
| 方向 | ${r.height>r.width?'竖屏 9:16':'横屏 16:9'} |
| 帧率 | ${r.fps} fps |
| 总帧数 | ${r.totalFrames.toLocaleString()} |
| 文件大小 | ${r.fileSize} MB |

---

## 二、内容类型识别

**识别为**: ${ct.label}
**描述**: ${ct.desc}
**识别特征**: ${(ct.tags||[]).join('、')}
**可信度评分**: ${ct._score?.score?.toFixed(2) || 'N/A'}

${ct._score?.matchedSignals?.length ? '**匹配特征**:\n' + ct._score.matchedSignals.map(s => `- ${s.reason} (通过率 ${(s.passRate*100).toFixed(0)}%)`).join('\n') : ''}

---

## 三、核心指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 平均亮度 | ${avgB} | ${+avgB>0.65?'明亮':(+avgB<0.3?'昏暗':'适中')} |
| 平均运动 | ${avgM} | ${+avgM<0.05?'静止':(+avgM<0.2?'平稳':'运动频繁')} |
| 场景切换 | ${r.sceneChanges.length} 处 | ${r.sceneChanges.length>0?'有剪辑点':'画面连续'} |

---

## 四、场景时间线

${phaseLines}

---

## 五、语音识别

${speech?.fullText || speech?.text ? `**转写文字（共${(speech.fullText||speech.text).length}字）**:

| 时间 | 内容 |
|------|------|
${speechLines}

**关键词**: ${speech.keywords?.highFreq?.slice(0,15)?.join(' / ')||'无'}
**动作词**: ${speech.keywords?.actions?.join(' / ')||'无'}
**情绪词**: ${speech.keywords?.emotions?.join(' / ')||'无'}` : '未检测到语音内容'}

---

## 六、帧分析数据

| 时间 | 主色调 | 亮度 | 运动 | 文字% |
|------|--------|------|------|-------|
${frameLines}

---

## 七、视频文案脚本

${script || '(无语音内容)'}

---

*由 Video Content Analyzer 自动生成*
`;
  $('reportMd').value = md;
}


function downloadReport() {
  if (!$('reportMd')?.value) return;
  const blob = new Blob([$('reportMd').value], {type:'text/markdown;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'video_analysis_' + new Date().toISOString().slice(0,10) + '.md';
  a.click();
  toast('报告已下载');
}


async function downloadFrames() {
  if (!frameImages.length) return;
  for (const f of frameImages) {
    const a = document.createElement('a');
    a.href = f.img;
    a.download = 'frame_' + f.t.toString().padStart(4,'0') + 's.jpg';
    a.click();
    await new Promise(r => setTimeout(r, 80));
  }
  toast('已下载 ' + frameImages.length + ' 张帧图片');
}


// ── Init ──
$('fileInput').addEventListener('change', e => { if (e.target.files[0]) processFile(e.target.files[0]); });
const zone = $('uploadZone');
zone?.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
zone?.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
zone?.addEventListener('drop', e => { e.preventDefault(); zone?.classList.remove('drag-over'); if (e.dataTransfer.files[0]) processFile(e.dataTransfer.files[0]); });

console.log('[v3] loaded');