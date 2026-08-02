# -*- coding: utf-8 -*-
import io

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with io.open(path, encoding='utf-8') as f:
    c = f.read()

# ---- 1) Replace deepStep1 block with provider-selector version ----
OLD1 = '''<div id="deepStep1" style="max-width:100%;overflow:hidden;margin-bottom:1.2rem;padding:1rem;background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;box-sizing:border-box;">
<div style="font-size:0.78rem;color:#6b7084;line-height:1.8;margin-bottom:1rem;">
&#128270; 基于「叙事主权破局 + 反资本共情 + 5A人群流转 + 实锤卖点种草 + 信任建立体系」五位一体方法论，生成九节结构化报告。<br>
&#9888; 支持 <strong style="color:#f87171;">SiliconFlow（硅基流动）</strong>等兼容 OpenAI 接口的大模型。
</div>
<div style="margin-bottom:0.9rem;">
<label style="display:block;font-size:0.75rem;color:#6b7084;margin-bottom:0.4rem;">API Key（仅本次本地使用，不上传任何服务器）</label>
<input id="deepApiKey" type="password" placeholder="sk-..." style="width:100%;padding:0.65rem 0.9rem;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;color:#e2e8f0;font-size:0.82rem;box-sizing:border-box;outline:none;height:42px;" />
</div>
<div style="font-size:0.72rem;color:#4a4d63;margin-bottom:1rem;">SiliconFlow：<a href="https://siliconflow.cn" target="_blank" style="color:#818cf8;">siliconflow.cn</a> → 个人中心 → API Key</div>
<div style="display:flex;gap:0.6rem;flex-wrap:wrap;align-items:center;">
<button id="btnTestKey" class="btn btn-secondary" onclick="testApiKey()">&#10004; 验证 Key</button>
<div id="deepKeyError" style="display:none;margin-top:0.7rem;font-size:0.75rem;color:#f87171;padding:0.6rem 0.8rem;background:#2d1515;border:1px solid #5c2a2a;border-radius:8px;line-height:1.7;max-width:100%;box-sizing:border-box;overflow-wrap:break-word;"></div>
</div>'''

NEW1 = '''<div id="deepStep1" style="max-width:100%;overflow:hidden;margin-bottom:1.2rem;padding:1rem;background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;box-sizing:border-box;">
<div style="font-size:0.78rem;color:#6b7084;line-height:1.8;margin-bottom:1rem;">
&#128270; 基于「叙事主权破局 + 反资本共情 + 5A人群流转 + 实锤卖点种草 + 信任建立体系」五位一体方法论，生成九节结构化报告。<br>
&#9888; 支持 <strong style="color:#f87171;">SiliconFlow（硅基流动）</strong>、<strong style="color:#4ade80;">Ollama（本地模型）</strong> 等兼容 OpenAI 接口的大模型。
</div>

<!-- 服务商选择 -->
<div style="margin-bottom:1rem;">
<label style="display:block;font-size:0.75rem;color:#6b7084;margin-bottom:0.5rem;">选择 AI 服务商</label>
<div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
<label style="display:flex;align-items:center;gap:0.35rem;font-size:0.78rem;color:#cbd5e1;padding:0.4rem 0.7rem;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;cursor:pointer;"><input type="radio" name="deepProvider" value="siliconflow" checked onchange="onProviderChange()"> SiliconFlow</label>
<label style="display:flex;align-items:center;gap:0.35rem;font-size:0.78rem;color:#cbd5e1;padding:0.4rem 0.7rem;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;cursor:pointer;"><input type="radio" name="deepProvider" value="ollama" onchange="onProviderChange()"> Ollama（本地）</label>
<label style="display:flex;align-items:center;gap:0.35rem;font-size:0.78rem;color:#cbd5e1;padding:0.4rem 0.7rem;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;cursor:pointer;"><input type="radio" name="deepProvider" value="zhipu" onchange="onProviderChange()"> 智谱</label>
</div>
</div>

<!-- SiliconFlow / 智谱：API Key -->
<div id="deepKeyBlock">
<div style="margin-bottom:0.9rem;">
<label style="display:block;font-size:0.75rem;color:#6b7084;margin-bottom:0.4rem;">API Key（仅本次本地使用，不上传任何服务器）</label>
<input id="deepApiKey" type="password" placeholder="sk-..." style="width:100%;padding:0.65rem 0.9rem;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;color:#e2e8f0;font-size:0.82rem;box-sizing:border-box;outline:none;height:42px;" />
</div>
<div style="font-size:0.72rem;color:#4a4d63;margin-bottom:1rem;">SiliconFlow：<a href="https://siliconflow.cn" target="_blank" style="color:#818cf8;">siliconflow.cn</a> → 个人中心 → API Key ｜ 智谱：<a href="https://open.bigmodel.cn" target="_blank" style="color:#818cf8;">open.bigmodel.cn</a></div>
<div style="display:flex;gap:0.6rem;flex-wrap:wrap;align-items:center;">
<button id="btnTestKey" class="btn btn-secondary" onclick="testApiKey()">&#10004; 验证 Key</button>
</div>
</div>

<!-- Ollama：本地模型 -->
<div id="deepOllamaBlock" style="display:none;">
<div style="margin-bottom:0.9rem;">
<label style="display:block;font-size:0.75rem;color:#6b7084;margin-bottom:0.4rem;">Ollama 地址（默认本地）</label>
<input id="deepOllamaBase" type="text" value="http://localhost:11434" style="width:100%;padding:0.65rem 0.9rem;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;color:#e2e8f0;font-size:0.82rem;box-sizing:border-box;outline:none;height:42px;" />
</div>
<div style="font-size:0.72rem;color:#4a4d63;margin-bottom:1rem;">确保已启动 Ollama（<code>ollama serve</code>），并已拉取模型（如 <code>ollama pull llama3.1</code>）。</div>
<div style="display:flex;gap:0.6rem;flex-wrap:wrap;align-items:center;">
<button id="btnTestOllama" class="btn btn-secondary" onclick="testOllama()">&#128268; 检测本地模型</button>
</div>
</div>

<div id="deepKeyError" style="display:none;margin-top:0.8rem;font-size:0.75rem;color:#f87171;padding:0.6rem 0.8rem;background:#2d1515;border:1px solid #5c2a2a;border-radius:8px;line-height:1.7;max-width:100%;box-sizing:border-box;overflow-wrap:break-word;"></div>
</div>'''

assert c.count(OLD1) == 1, 'OLD1 count = %d' % c.count(OLD1)
c = c.replace(OLD1, NEW1)

# ---- 2) deepKeyOk text generic ----
c = c.replace('&#10004; API Key 验证通过，请选择模型',
              '&#10004; 连接成功，请选择模型')

# ---- 3) deepGoStep1: resync provider blocks at end ----
OLD3 = '''  $('deepReportStatus').textContent = '';
}

async function testApiKey() {'''
NEW3 = '''  $('deepReportStatus').textContent = '';
  try { if (typeof onProviderChange === 'function') onProviderChange(); } catch(e) {}
}

function onProviderChange() {
  const p = (document.querySelector('input[name="deepProvider"]:checked') || {}).value || 'siliconflow';
  $('deepKeyError').style.display = 'none';
  if (p === 'ollama') {
    $('deepKeyBlock').style.display = 'none';
    $('deepOllamaBlock').style.display = 'block';
  } else {
    $('deepKeyBlock').style.display = 'block';
    $('deepOllamaBlock').style.display = 'none';
  }
}

async function testOllama() {
  const base = ($('deepOllamaBase').value || 'http://localhost:11434').trim();
  $('deepKeyError').style.display = 'none';
  $('btnTestOllama').disabled = true;
  $('btnTestOllama').textContent = '检测中...';
  try {
    const resp = await fetch(TRANSCRIBE_BASE + '/api/test-api-key', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({provider: 'ollama', ollama_base: base}),
    });
    const data = await resp.json();
    if (data.ok) {
      _deepApiVerified = true;
      const sel = $('deepModel');
      sel.innerHTML = '';
      data.available_models.forEach(function(m) {
        const opt = document.createElement('option');
        opt.value = m[0]; opt.textContent = m[1];
        if (m[0] === data.model) opt.selected = true;
        sel.appendChild(opt);
      });
      _deepModel = data.model || (data.available_models[0] ? data.available_models[0][0] : '');
      $('deepModelTip').textContent = '服务商：Ollama  ·  当前模型：' + _deepModel;
      $('deepStep1').style.display = 'none';
      $('deepStep2').style.display = 'block';
    } else {
      _deepApiVerified = false;
      showKeyError(data.error || 'Ollama 检测失败');
    }
  } catch(e) {
    _deepApiVerified = false;
    showKeyError('网络请求失败：' + e.message);
  } finally {
    $('btnTestOllama').disabled = false;
    $('btnTestOllama').textContent = '检测本地模型';
  }
}

async function testApiKey() {'''
assert c.count(OLD3) == 1, 'OLD3 count = %d' % c.count(OLD3)
c = c.replace(OLD3, NEW3)

# ---- 4) testApiKey: read provider + send it ----
c = c.replace(
    "  if (!key) { showKeyError('API Key 不能为空'); return; }\n  $('deepKeyError').style.display = 'none';",
    "  if (!key) { showKeyError('API Key 不能为空'); return; }\n  const provider = (document.querySelector('input[name=\"deepProvider\"]:checked') || {}).value || 'siliconflow';\n  $('deepKeyError').style.display = 'none';")
c = c.replace(
    "body: JSON.stringify({api_key: key}),",
    "body: JSON.stringify({api_key: key, provider: provider}),")

# ---- 5) doDeepAnalysis: read provider + ollama_base, send them ----
c = c.replace(
    "  const apiKey = ($('deepApiKey').value || '').trim();\n  const model  = ($('deepModel').value || _deepModel || '').trim();\n  const payload = {",
    "  const provider = (document.querySelector('input[name=\"deepProvider\"]:checked') || {}).value || 'siliconflow';\n  const ollamaBase = ($('deepOllamaBase').value || '').trim();\n  const apiKey = ($('deepApiKey').value || '').trim();\n  const model  = ($('deepModel').value || _deepModel || '').trim();\n  const payload = {")
c = c.replace(
    "    api_key: apiKey,\n    model: model,\n  };",
    "    api_key: apiKey,\n    model: model,\n    provider: provider,\n    ollama_base: ollamaBase,\n  };")

with io.open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print('patched OK')
