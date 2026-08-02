"""修复深度分析功能：API Key 测试 + 模型选择 + 清缓存"""
import re, os

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
c = open(path, encoding='utf-8').read()
original = c

# ── 1. processFile: 上传时清空所有缓存 ──
# 找 speechResult = null; 后加 analysisResult 和 deepReportCache
old_reset = "  speechResult = null;\n  transcribeJobId = null;\n  clearInterval(transcribePollTimer);"
new_reset = """  speechResult = null;
  analysisResult = null;
  deepReportCache = null;
  transcribeJobId = null;
  clearInterval(transcribePollTimer);"""
if old_reset in c:
    c = c.replace(old_reset, new_reset, 1)
    print("✓ processFile cache clear added")
else:
    print("WARNING: processFile reset not found")

# ── 2. processFile 末尾（transcribeJobId = jobId 前）也加清缓存 ──
# 查找上传成功后的设置，找到那行
old_tj = "      transcribeJobId = jobId;"
if "      transcribeJobId = jobId;" in c:
    c = c.replace(
        "      speechResult = null;\n      transcribeJobId = null;",
        "      speechResult = null;\n      analysisResult = null;\n      deepReportCache = null;\n      transcribeJobId = null;",
    )
    print("✓ processFile second cache clear added")

# ── 3. 重写 tabDeepReport HTML ──
old_tab = """<div id="tabDeepReport" class="tab-panel">
<div class="section">
<div class="section-title">&#128270; <span>短视频文案深度拆解报告</span> <span id="deepReportStatus" style="font-size:0.72rem;color:#6b7084;font-weight:400;"></span></div>
<div id="deepReportIntro" style="margin-bottom:1rem;padding:0.85rem;background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;">
<div style="font-size:0.76rem;color:#6b7084;line-height:1.7;margin-bottom:0.8rem;">
&#128270; 基于「叙事主权破局 + 反资本共情 + 5A人群流转 + 实锤卖点种草 + 信任建立体系」五位一体方法论，生成九节结构化报告。<br>
&#9888; 支持 <strong style="color:#f87171;">SiliconFlow（硅基流动）</strong>等兼容 OpenAI 接口的大模型 API。
</div>
<div style="margin-bottom:0.8rem;">
<label style="display:block;font-size:0.73rem;color:#6b7084;margin-bottom:0.35rem;">API Key（仅本次使用，不上传服务器）</label>
<input id="deepApiKey" type="password" placeholder="sk-..." style="width:100%;padding:0.5rem 0.75rem;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;color:#e2e8f0;font-size:0.78rem;box-sizing:border-box;outline:none;" onkeydown="if(event.key==='Enter')doDeepAnalysis()" />
</div>
<div style="font-size:0.7rem;color:#4a4d63;margin-bottom:0.8rem;">SiliconFlow 地址：<a href="https://siliconflow.cn" target="_blank" style="color:#818cf8;">siliconflow.cn</a> → 个人中心 → API Key</div>
<button id="btnDeepAnalyze" class="btn btn-primary" onclick="doDeepAnalysis()">&#127919; 启动深度分析</button>
</div>"""

new_tab = """<div id="tabDeepReport" class="tab-panel">
<div class="section">
<div class="section-title">&#128270; <span>短视频文案深度拆解报告</span> <span id="deepReportStatus" style="font-size:0.72rem;color:#6b7084;font-weight:400;"></span></div>

<!-- Step 1: API Key 输入 -->
<div id="deepStep1" style="margin-bottom:1rem;padding:0.85rem;background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;">
<div style="font-size:0.76rem;color:#6b7084;line-height:1.7;margin-bottom:0.8rem;">
&#128270; 基于「叙事主权破局 + 反资本共情 + 5A人群流转 + 实锤卖点种草 + 信任建立体系」五位一体方法论，生成九节结构化报告。<br>
&#9888; 支持 <strong style="color:#f87171;">SiliconFlow（硅基流动）</strong>等兼容 OpenAI 接口的大模型。
</div>
<div style="margin-bottom:0.7rem;">
<label style="display:block;font-size:0.73rem;color:#6b7084;margin-bottom:0.35rem;">API Key（仅本次本地使用，不上传任何服务器）</label>
<input id="deepApiKey" type="password" placeholder="sk-..." style="width:100%;padding:0.5rem 0.75rem;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;color:#e2e8f0;font-size:0.78rem;box-sizing:border-box;outline:none;" />
</div>
<div style="font-size:0.7rem;color:#4a4d63;margin-bottom:0.8rem;">SiliconFlow：<a href="https://siliconflow.cn" target="_blank" style="color:#818cf8;">siliconflow.cn</a> → 个人中心 → API Key</div>
<button id="btnTestKey" class="btn btn-secondary" onclick="testApiKey()" style="margin-right:0.5rem;">&#10004; 验证 Key</button>
<div id="deepKeyError" style="display:none;margin-top:0.6rem;font-size:0.73rem;color:#f87171;padding:0.5rem;background:#2d1515;border:1px solid #5c2a2a;border-radius:8px;line-height:1.6;"></div>
</div>

<!-- Step 2: 模型选择（验证通过后显示） -->
<div id="deepStep2" style="display:none;margin-bottom:1rem;padding:0.85rem;background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;">
<div id="deepKeyOk" style="font-size:0.73rem;color:#4ade80;margin-bottom:0.7rem;">&#10004; API Key 验证通过，请选择模型</div>
<div style="margin-bottom:0.8rem;">
<label style="display:block;font-size:0.73rem;color:#6b7084;margin-bottom:0.35rem;">选择模型</label>
<select id="deepModel" style="width:100%;padding:0.5rem 0.75rem;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;color:#e2e8f0;font-size:0.78rem;box-sizing:border-box;outline:none;">
</select>
</div>
<div style="font-size:0.7rem;color:#4a4d63;margin-bottom:0.8rem;">
<span id="deepModelTip"></span>
</div>
<button id="btnDeepAnalyze" class="btn btn-primary" onclick="doDeepAnalysis()">&#127919; 启动深度分析</button>
<div style="margin-top:0.5rem;"><button class="btn btn-secondary" onclick="deepGoStep1()" style="font-size:0.72rem;padding:0.3rem 0.6rem;">&#8592; 重新填写 Key</button></div>
</div>"""

if old_tab in c:
    c = c.replace(old_tab, new_tab)
    print("✓ tabDeepReport HTML rewritten")
else:
    print("WARNING: tabDeepReport HTML not found, trying alternate match")
    # Try partial
    if '<div id="tabDeepReport"' in c:
        print("  → tabDeepReport div found (partial), will try regex")
    else:
        print("  → tabDeepReport div NOT FOUND")

# ── 4. 重写 doDeepAnalysis ──
old_doDeep = """function doDeepAnalysis() {
  if (!analysisResult || !speechResult) {
    showDeepError('请先上传视频并完成转写后再进行分析。');
    return;
  }
  const text = speechResult.text || speechResult.fullText || '';
  if (!text || text.length < 10) {
    showDeepError('转写文字过短，无法进行深度分析。请确认视频有语音内容。');
    return;
  }

  // UI: show loading
  $('deepReportIntro').style.display = 'none';
  $('deepReportLoading').style.display = 'block';
  $('deepReportContent').style.display = 'none';
  $('deepReportError').style.display = 'none';
  $('deepReportStatus').textContent = '分析中...';
  setDeepProgress(0, '正在发送分析请求...');

  const apiKey = ($('deepApiKey').value || '').trim();
  const payload = {
    transcription: {
      text: text,
      language: speechResult.language || 'zh',
      segments: speechResult.segments || [],
      keywords: speechResult.keywords || {}
    },
    analysis: analysisResult,
    video_meta: {
      width: analysisResult.width,
      height: analysisResult.height,
      fps: analysisResult.fps
    },
    api_key: apiKey
  };

  fetch(TRANSCRIBE_BASE + '/api/analyze-copy', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  })
  .then(r => r.json())
  .then(data => {
    if (!data.has_llm) {
      showDeepError('&#9888; API Key 无效或接口调用失败。<br><br>请检查：<br>1. Key 是否正确（以 <code>sk-</code> 开头）<br>2. SiliconFlow 账户是否有余额<br>3. 是否已填入 Key（不可为空）<br><br>错误详情：' + (data.error || 'unknown'));
      return;
    }
    if (data.error) {
      showDeepError('分析失败：' + data.error);
      return;
    }
    deepReportCache = data.report;
    renderDeepReport(data.report);
    $('deepReportLoading').style.display = 'none';
    $('deepReportContent').style.display = 'block';
    $('deepReportStatus').textContent = '✓ 分析完成 · ' + data.model;
    setDeepProgress(100, '分析完成！');
  })
  .catch(err => {
    showDeepError('网络请求失败：' + err.message + '<br><br>请确认转写服务（端口 8766）已启动。');
    $('deepReportLoading').style.display = 'none';
    $('deepReportIntro').style.display = 'block';
  });
}"""

new_doDeep = """// ── 深度分析（九节结构） ──
let deepReportCache = null;
let _deepApiVerified = false;   // Key 是否已验证
let _deepModel = '';            // 选中的模型

// 三步切换
function deepGoStep1() {
  _deepApiVerified = false;
  _deepModel = '';
  $('deepStep1').style.display = 'block';
  $('deepStep2').style.display = 'none';
  $('deepReportLoading').style.display = 'none';
  $('deepReportContent').style.display = 'none';
  $('deepReportError').style.display = 'none';
  $('deepKeyError').style.display = 'none';
  $('deepReportStatus').textContent = '';
}

// Step 1: 验证 Key
async function testApiKey() {
  const key = ($('deepApiKey').value || '').trim();
  if (!key) { showKeyError('API Key 不能为空'); return; }
  $('deepKeyError').style.display = 'none';
  $('btnTestKey').disabled = true;
  $('btnTestKey').textContent = '验证中...';
  try {
    const resp = await fetch(TRANSCRIBE_BASE + '/api/test-api-key', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: key}),
    });
    const data = await resp.json();
    if (data.ok) {
      _deepApiVerified = true;
      // 填充模型列表
      const sel = $('deepModel');
      sel.innerHTML = '';
      data.available_models.forEach(function(m) {
        const opt = document.createElement('option');
        opt.value = m[0]; opt.textContent = m[1];
        if (m[0] === data.model) opt.selected = true;
        sel.appendChild(opt);
      });
      _deepModel = data.model || data.available_models[0][0];
      $('deepModelTip').textContent = '服务商：' + data.provider + '  ·  当前模型：' + _deepModel;
      $('deepStep1').style.display = 'none';
      $('deepStep2').style.display = 'block';
    } else {
      _deepApiVerified = false;
      showKeyError(data.error || '验证失败，请检查 Key 是否正确');
    }
  } catch(e) {
    _deepApiVerified = false;
    showKeyError('网络请求失败：' + e.message);
  } finally {
    $('btnTestKey').disabled = false;
    $('btnTestKey').textContent = '✓ 验证 Key';
  }
}

function showKeyError(msg) {
  $('deepKeyError').innerHTML = '&#9888; ' + msg;
  $('deepKeyError').style.display = 'block';
}

function doDeepAnalysis() {
  if (!analysisResult || !speechResult) {
    showDeepError('请先上传视频并完成转写后再进行分析。');
    return;
  }
  const text = speechResult.text || speechResult.fullText || '';
  if (!text || text.length < 10) {
    showDeepError('转写文字过短，无法进行深度分析。请确认视频有语音内容。');
    return;
  }

  // UI: show loading
  $('deepStep2').style.display = 'none';
  $('deepReportLoading').style.display = 'block';
  $('deepReportContent').style.display = 'none';
  $('deepReportError').style.display = 'none';
  $('deepReportStatus').textContent = '分析中...';
  setDeepProgress(0, '正在发送分析请求...');

  const apiKey = ($('deepApiKey').value || '').trim();
  const model  = ($('deepModel').value  || _deepModel || '').trim();
  const payload = {
    transcription: {
      text: text,
      language: speechResult.language || 'zh',
      segments: speechResult.segments || [],
      keywords: speechResult.keywords || {}
    },
    analysis: analysisResult,
    video_meta: {
      width: analysisResult.width,
      height: analysisResult.height,
      fps: analysisResult.fps
    },
    api_key: apiKey,
    model: model,
  };

  fetch(TRANSCRIBE_BASE + '/api/analyze-copy', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  })
  .then(r => r.json())
  .then(data => {
    if (!data.has_llm || data.error) {
      const errMsg = data.error || 'API 调用失败';
      showDeepError(errMsg + '<br><br><button class="btn btn-secondary" onclick="deepGoStep1()" style="margin-top:0.5rem;">&#8592; 重新填写 Key</button>');
      return;
    }
    deepReportCache = data.report;
    renderDeepReport(data.report);
    $('deepReportLoading').style.display = 'none';
    $('deepReportContent').style.display = 'block';
    $('deepReportStatus').textContent = '✓ 分析完成 · ' + (data.model || model);
    setDeepProgress(100, '分析完成！');
  })
  .catch(err => {
    showDeepError('网络请求失败：' + err.message + '<br><br><button class="btn btn-secondary" onclick="deepGoStep1()" style="margin-top:0.5rem;">&#8592; 重新填写 Key</button>');
    $('deepReportLoading').style.display = 'none';
  });
}"""

if old_doDeep in c:
    c = c.replace(old_doDeep, new_doDeep)
    print("✓ doDeepAnalysis rewritten")
else:
    print("WARNING: doDeepAnalysis not found exactly")
    # Try partial
    if "function doDeepAnalysis()" in c:
        print("  → function doDeepAnalysis found (partial)")
    else:
        print("  → function doDeepAnalysis NOT FOUND")

# ── 5. 删除旧的深度分析注释行（如果残留） ──
old_comment = "// ── 深度分析（九节结构） ──\nlet deepReportCache = null;\n\nfunction doDeepAnalysis() {"
if old_comment in c:
    c = c.replace(old_comment, new_doDeep[:50])  # won't match anyway, already replaced
    print("cleaned old comment")

# ── 6. 写回文件 ──
f = open(path, 'w', encoding='utf-8')
f.write(c)
f.close()

print(f"\nFile size: {os.path.getsize(path):,} bytes")
print("Done.")
