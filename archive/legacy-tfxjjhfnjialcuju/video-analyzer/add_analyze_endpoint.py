"""添加 /api/analyze-copy 端点 到 transcribe_server.py"""

f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'r', encoding='utf-8')
c = f.read()
f.close()

# 检查是否已存在
if '/api/analyze-copy' in c:
    print('Endpoint already exists')
    exit(0)

ANALYZE_ENDPOINT = '''

# ─────────────────────────────────────────────
# 文案深度分析端点（需要 LLM API Key）
# 环境变量：LLM_API_KEY / LLM_BASE_URL
# ─────────────────────────────────────────────

ANALYZE_PROMPT = """你是一位顶尖的短视频带货文案拆解专家，擅长将口播文案拆解为结构统一、颗粒度到秒、可直接指导编导复刻的标准化报告。

## 输入数据
{input_data}

## 任务
严格按照以下九节结构输出。每节必须有实质内容，不允许"参照原文"或"此处省略"。

### 一句话总结（一行）
格式：「核心结论 · 流量打法 · 叙事主权破局点」，三点用 → 连接
示例：「超声刀无痛抗衰 → 开场反常识炮轰+结尾限时逼单 → 破"贵=好"叙事 · 建"安全>效果"标准 · 立"敢说真话"人设」

### 第一节 · 原文基础信息
- 逐字稿全文（保留原文，只做繁→简）
- 表层口播逻辑：用「→」连接，≤6步

### 第二节 · 深度反向拆解
- 风格调性（1句话）
- 观众心理路径（时间顺序，3~5个转折点）
- 3~5条可迁移底层情绪（不是表面技巧，是人性驱动）
- 叙事主权4步拆解：
  1. 破霸权：（具体是什么谎言/霸权）
  2. 建标准：（用什么事实/数据重建标准）
  3. 立人设：（主角的人设是什么）
  4. 收闭环：（怎么把情绪转化为信任）
- 跑量优势（3条，简短）

### 第三节 · 口播逐段拆解
用表格输出：
| 预估时长 | 内容模块 | 原文内容 | 核心作用 | 叙事主权标注 | 算法增益 | 5A标注 |
模块分类：开场钩子 / 产品介绍 / 效果展示 / 信任背书 / 行动召唤 / 其他
叙事主权标注：破霸权 / 建标准 / 立人设 / 收闭环
算法增益：完播驱动 / 点赞驱动 / 评论驱动 / 分享驱动 / 关注驱动
5A标注：A1(3秒) / A2(前3分位) / A3(中段) / A4(后3分位) / A5(结尾)

### 第四节 · 分镜头拆解
用表格输出：
| 镜头# | 时长 | 景别+运镜 | 画面内容 | 对应口播 | 情绪流转 | 视觉实锤 |
景别：特写/近景/中景/全景/远景/文字展示
运镜：固定/推进/拉远/摇镜/跟拍/升降
视觉实锤：具体画面细节（如"特写：超声刀探头接触皮肤，无红肿"）

### 第五节 · 5A人群流转
用表格输出：
| 人群层级 | 作用强度 | 核心流转价值 | 完整流转路径 |
流转路径示例：A1(开场反常识) → A2(产品介绍) → A3(效果对比) → A4(背书强化) → A5(限时逼单)
作用强度：★★★★★（最强）到 ★☆☆☆☆（辅助）

### 第六节 · 爆款文案库
用表格输出：
| 文案分类 | 文案内容 | 预估转化率 | 预估完播率 | 使用场景 |
每模块≥3条替代文案，保持原文人设语气。
文案分类：开场钩子 / 产品卖点 / 效果描述 / 信任背书 / 行动召唤

### 第七节 · 可复刻对标行业
3~5个相邻品类，每条格式：
「推翻 **X** 旧叙事 → 建立 **Y** 新标准」
示例：「推翻"进口=高端"旧叙事 → 建立"成分认证=可信"新标准」

### 第八节 · 团队落地执行要点
5~6条，每条一条可执行指令，格式：
- 【叙事一致性】：...
- 【实锤优先】：...
- 【背书强化】：...
- 【反攻击预案】：...
- 【人群侧重】：...
- 【分镜实操】：...

## 约束
- 基于原文事实，不编造数据；缺失信息用【推断】标注
- 时间轴秒级，覆盖率100%，不允许"其余部分同理"
- 替代文案语气/情绪强度与原文一致，不可降维
- 全部用Markdown标准表格输出"""

def call_llm_analyze(input_data: str, api_key: str = None, base_url: str = None) -> dict:
    """调用 LLM 生成九节分析报告"""
    import requests

    api_key = api_key or os.environ.get('LLM_API_KEY', '')
    base_url = base_url or os.environ.get('LLM_BASE_URL', '')
    
    if not api_key:
        return {"error": "LLM_API_KEY not configured", "available": False}

    if not base_url:
        base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "glm-4-flash",
        "messages": [
            {"role": "system", "content": "你是一位专业的短视频内容分析专家。请严格按照用户要求的九节格式输出结构化报告，用Markdown格式，包含所有表格。不要省略任何节的内容。"},
            {"role": "user", "content": ANALYZE_PROMPT.format(input_data=input_data)}
        ],
        "temperature": 0.3,
        "max_tokens": 8192
    }

    try:
        resp = requests.post(f"{base_url}/chat/completions", 
                            headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"report": content, "available": True, "model": "glm-4-flash"}
        else:
            return {"error": f"API error {resp.status_code}: {resp.text[:200]}", "available": True}
    except Exception as e:
        return {"error": str(e), "available": True}


@app.route("/api/analyze-copy", methods=["POST"])
def api_analyze_copy():
    """
    文案深度分析（九节结构）
    请求体：
    {
      "transcription": { text, language, segments[{start,end,text}] },
      "analysis": { name, duration, frames[{t,brightness,hue,sat,motion,skinRatio,textRatio,dominantColor,shotType}], contentType, sceneChanges, phases },
      "video_meta": { width, height, fps }
    }
    """
    try:
        body = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    transcription = body.get("transcription", {})
    analysis = body.get("analysis", {})
    video_meta = body.get("video_meta", {})

    full_text = transcription.get("text", "") or transcription.get("fullText", "")
    if not full_text:
        return jsonify({"error": "No transcription text available"}), 400

    # 构建输入数据摘要（供 LLM 分析）
    segments = transcription.get("segments", [])
    seg_text = "\n".join([f"[{s.get('start',0):.1f}s-{s.get('end',0):.1f}s] {s.get('text','')}" 
                          for s in segments])

    content_type = analysis.get("contentType", {}) or {}
    frames = analysis.get("frames", [])
    
    # 帧摘要
    frame_summary = []
    for f in frames[:20]:  # 最多20帧
        frame_summary.append({
            "t": f"{f.get('t', 0):.1f}s",
            "brightness": round(f.get('brightness', 0), 3),
            "dominant_color": f.get('dominantColor', 'N/A'),
            "shot_type": f.get('shotType', 'N/A'),
            "has_text": (f.get('textRatio', 0)) > 5,
            "skin_detected": (f.get('skinRatio', 0)) > 0.05,
        })

    input_data = f"""
【视频基本信息】
- 文件名：{analysis.get('name', '未知')}
- 时长：{analysis.get('duration', 0):.1f}秒
- 分辨率：{video_meta.get('width',0)}x{video_meta.get('height',0)}
- 内容类型：{content_type.get('label','未知')} — {content_type.get('desc','')}

【逐字稿（按时间分段）】
{seg_text}

【帧画面摘要（前{max(len(frames),20)}帧）】
{chr(10).join([f"- {f['t']} | 亮度:{f['brightness']} | 主色:{f['dominant_color']} | 景别:{f['shot_type']} | 字幕:{'有' if f['has_text'] else '无'} | 人物:{'有' if f['skin_detected'] else '无'}" for f in frame_summary])}

【场景分段】
{chr(10).join([f"- {p.get('label','')} (@{p.get('start',0):.0f}s-{p.get('end',0):.0f}s, {p.get('end',0)-p.get('start',0):.1f}秒)" for p in analysis.get('phases', [])])}

【关键词】
高频词：{(transcription.get('keywords') or {}).get('highFreq', [])[:20]}
动作词：{(transcription.get('keywords') or {}).get('actions', [])[:10]}
情绪词：{(transcription.get('keywords') or {}).get('emotions', [])[:10]}
"""

    result = call_llm_analyze(input_data)
    
    return jsonify({
        "status": "ok",
        "has_llm": result.get("available", False),
        "report": result.get("report", None),
        "error": result.get("error", None),
        "segments_count": len(segments),
        "frames_count": len(frames),
        "full_text_length": len(full_text),
        "model": result.get("model", None)
    })

'''

# 找到最后一个 @app.route 的位置，在其后添加
last_route_line = None
for i, line in enumerate(c.split('\n')):
    if '@app.route' in line:
        last_route_line = i

lines = c.split('\n')
# 在最后一个 @app.route 块后面添加新端点
# 找到最后一个函数的结束位置
insert_after = len(lines) - 2  # 在文件倒数第2行之前

new_lines = lines + [''] + ANALYZE_ENDPOINT.split('\n')

f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'w', encoding='utf-8')
f.write('\n'.join(new_lines))
f.close()

print('Done. New lines:', len(new_lines))
print('ANALYZE_ENDPOINT added to transcribe_server.py')
