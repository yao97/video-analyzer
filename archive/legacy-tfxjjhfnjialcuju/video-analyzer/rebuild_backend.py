"""重建 transcribe_server.py：保留原始内容 + 新的 analyze-copy 端点"""
f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'r', encoding='utf-8')
c = f.read()
f.close()
lines = c.split('\n')

# Find the # ── 启动 ── line
startup_idx = None
for i, l in enumerate(lines):
    if '─ 启动 ──' in l:
        startup_idx = i
        break

print(f'# ── 启动 ── at line {startup_idx+1}')
print(f'Total lines: {len(lines)}')

# Keep lines 0 to startup_idx (inclusive the # ── 启动 ── line)
# But we need to also keep the if __name__ block after it
# The startup block ends at 'app.run(...)'
app_run_idx = None
for i in range(startup_idx, len(lines)):
    if 'app.run(host=args.host' in lines[i]:
        app_run_idx = i
        break

print(f'app.run at line {app_run_idx+1}')

# Keep lines 0 to app_run_idx (the startup block)
# Then add the new endpoint
new_endpoint = '''


# ============================================================
# 文案深度分析端点（需要 LLM API Key）
# ============================================================

def call_llm_analyze(input_data: str, api_key: str = None, base_url: str = None) -> dict:
    import requests
    api_key = api_key or os.environ.get('LLM_API_KEY', '')
    base_url = base_url or os.environ.get(
        'LLM_BASE_URL',
        'https://open.bigmodel.cn/api/paas/v4/chat/completions'
    )
    if not api_key:
        return {"error": "LLM_API_KEY not configured", "available": False}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    system_prompt = (
        "你是一位专业的短视频内容分析专家。请严格按照九节格式输出结构化报告，"
        "用Markdown格式，包含所有表格，每节必须有实质内容。"
    )
    user_prompt = (
        "你是一位顶尖的短视频带货文案拆解专家，擅长将口播文案拆解为结构统一、"
        "颗粒度到秒、可直接指导编导复刻的标准化报告。\n\n"
        "## 输入数据\n" + input_data + "\n\n"
        "## 任务\n"
        "严格按照以下九节结构输出，每节必须有实质内容，不允许参照原文或此处省略。\n\n"
        "### 一句话总结（一行）\n"
        "格式：核心结论 · 流量打法 · 叙事主权破局点，三点用箭头连接。\n\n"
        "### 第一节 · 原文基础信息\n"
        "- 逐字稿全文（保留原文，只做繁转简）\n"
        "- 表层口播逻辑：用箭头连接，不超过6步\n\n"
        "### 第二节 · 深度反向拆解\n"
        "- 风格调性（1句话）\n"
        "- 观众心理路径（时间顺序，3到5个转折点）\n"
        "- 3到5条可迁移底层情绪（人性驱动，不是表面技巧）\n"
        "- 叙事主权4步拆解：\n"
        "  1. 破霸权：具体是什么谎言或霸权\n"
        "  2. 建标准：用什么事实或数据重建标准\n"
        "  3. 立人设：主角的人设是什么\n"
        "  4. 收闭环：怎么把情绪转化为信任\n"
        "- 跑量优势（3条，简短）\n\n"
        "### 第三节 · 口播逐段拆解\n"
        "用表格输出，包含：预估时长、内容模块、原文内容、核心作用、叙事主权标注、算法增益、5A标注。\n"
        "模块分类：开场钩子、产品介绍、效果展示、信任背书、行动召唤、其他。\n"
        "叙事主权标注：破霸权、建标准、立人设、收闭环。\n"
        "算法增益：完播驱动、点赞驱动、评论驱动、分享驱动、关注驱动。\n"
        "5A标注：A1（3秒）、A2（前三分位）、A3（中段）、A4（后三分位）、A5（结尾）。\n\n"
        "### 第四节 · 分镜头拆解\n"
        "用表格输出，包含：镜头编号、时长、景别加运镜、画面内容、对应口播、情绪流转、视觉实锤。\n"
        "景别：特写、近景、中景、全景、远景、文字展示。\n"
        "运镜：固定、推进、拉远、摇镜、跟拍、升降。\n"
        "视觉实锤：具体画面细节，不允许省略。\n\n"
        "### 第五节 · 5A人群流转\n"
        "用表格输出，包含：人群层级、作用强度（1到5星）、核心流转价值、完整流转路径。\n\n"
        "### 第六节 · 爆款文案库\n"
        "用表格输出，包含：文案分类、文案内容、预估转化率、预估完播率、使用场景。\n"
        "每模块至少3条替代文案，保持原文人设语气。\n"
        "文案分类：开场钩子、产品卖点、效果描述、信任背书、行动召唤。\n\n"
        "### 第七节 · 可复刻对标行业\n"
        "3到5个相邻品类，每条格式：推翻 X 旧叙事、然后建立 Y 新标准。\n\n"
        "### 第八节 · 团队落地执行要点\n"
        "5到6条，每条一条可执行指令。\n"
        "- 【叙事一致性】：……\n"
        "- 【实锤优先】：……\n"
        "- 【背书强化】：……\n"
        "- 【反攻击预案】：……\n"
        "- 【人群侧重】：……\n"
        "- 【分镜实操】：……\n\n"
        "## 约束\n"
        "- 基于原文事实，不编造数据；缺失信息用【推断】标注\n"
        "- 时间轴秒级，覆盖率100%，不允许其余部分同理\n"
        "- 替代文案语气和情绪强度与原文一致，不可降维\n"
        "- 全部用Markdown标准表格输出"
    )

    payload = {
        "model": "glm-4-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 8192
    }
    try:
        resp = requests.post(
            base_url + "/chat/completions",
            headers=headers, json=payload, timeout=120
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"report": content, "available": True, "model": "glm-4-flash"}
        else:
            return {
                "error": f"API error {resp.status_code}: {resp.text[:200]}",
                "available": True
            }
    except Exception as e:
        return {"error": str(e), "available": True}


@app.route("/api/analyze-copy", methods=["POST"])
def api_analyze_copy():
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

    segments = transcription.get("segments", [])
    seg_lines = []
    for s in segments:
        seg_lines.append(
            f"[{s.get('start', 0):.1f}s-{s.get('end', 0):.1f}s] {s.get('text', '')}"
        )
    seg_text = "\n".join(seg_lines)

    content_type = analysis.get("contentType", {}) or {}
    frames = analysis.get("frames", [])
    frame_lines = []
    for f in frames[:20]:
        frame_lines.append(
            f"- {f.get('t', 0):.1f}s | "
            f"亮度:{round(f.get('brightness', 0), 3)} | "
            f"主色:{f.get('dominantColor', 'N/A')} | "
            f"景别:{f.get('shotType', 'N/A')} | "
            f"字幕:{'有' if f.get('textRatio', 0) > 5 else '无'} | "
            f"人物:{'有' if f.get('skinRatio', 0) > 0.05 else '无'}"
        )
    phase_lines = []
    for p in analysis.get("phases", []):
        phase_lines.append(
            f"- {p.get('label', '')} "
            f"(@{p.get('start', 0):.0f}s-{p.get('end', 0):.0f}s, "
            f"{p.get('end', 0) - p.get('start', 0):.1f}秒)"
        )

    kw = transcription.get("keywords", {}) or {}
    input_data = (
        "【视频基本信息】\n"
        f"- 文件名：{analysis.get('name', '未知')}\n"
        f"- 时长：{analysis.get('duration', 0):.1f}秒\n"
        f"- 分辨率：{video_meta.get('width', 0)}x{video_meta.get('height', 0)}\n"
        f"- 内容类型：{content_type.get('label', '未知')} — {content_type.get('desc', '')}\n\n"
        "【逐字稿（按时间分段）】\n" + seg_text + "\n\n"
        "【帧画面摘要（前20帧）】\n" + "\n".join(frame_lines) + "\n\n"
        "【场景分段】\n" + "\n".join(phase_lines) + "\n\n"
        "【关键词】\n"
        f"高频词：{kw.get('highFreq', [])[:20]}\n"
        f"动作词：{kw.get('actions', [])[:10]}\n"
        f"情绪词：{kw.get('emotions', [])[:10]}\n"
    )

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

# Keep lines 0 to app_run_idx (inclusive), then append new_endpoint
kept_lines = lines[:app_run_idx + 1]
new_content = '\n'.join(kept_lines) + new_endpoint

f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'w', encoding='utf-8')
f.write(new_content)
f.close()

print(f'Written {len(new_content)} chars, {new_content.count(chr(10))+1} lines')

# Verify syntax
try:
    import ast
    ast.parse(new_content)
    print('SYNTAX OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR at line {e.lineno}: {e.msg}')
    print(f'  File line {e.lineno}: {repr(new_content.split(chr(10))[e.lineno-1][:80])}')
