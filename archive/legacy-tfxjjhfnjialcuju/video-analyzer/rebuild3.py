"""重建 transcribe_server.py — 使用列表逐行写入，避免字符串转义问题"""
import os, ast

# 读取当前文件，取到 app.run 那一行
f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'r', encoding='utf-8')
lines = f.readlines()
f.close()

# 找 app.run 行
app_run_idx = None
for i, l in enumerate(lines):
    if 'app.run(host=args.host' in l:
        app_run_idx = i
        break
print(f'app.run at line {app_run_idx+1}, total {len(lines)} lines')

# 取原始前缀（不含 app.run 之后的任何内容）
prefix_lines = lines[:app_run_idx + 1]

# 新端点内容（逐行列出，避免转义问题）
new_lines = [
    '',
    '',
    '# ============================================================',
    '# 文案深度分析端点（需要 LLM API Key）',
    '# ============================================================',
    '',
    'def call_llm_analyze(input_data_str, api_key=None, base_url=None):',
    '    import requests',
    '    api_key = api_key or os.environ.get("LLM_API_KEY", "")',
    '    base_url = base_url or os.environ.get(',
    '        "LLM_BASE_URL",',
    '        "https://open.bigmodel.cn/api/paas/v4/chat/completions"',
    '    )',
    '    if not api_key:',
    '        return {"error": "LLM_API_KEY not configured", "available": False}',
    '    headers_dict = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}',
    '    system_prompt = (',
    '        "你是一位专业的短视频内容分析专家。请严格按照九节格式输出结构化报告，',
    '        "用Markdown格式，包含所有表格，每节必须有实质内容。"',
    '    )',
    '    user_prompt_lines = [',
    '        "你是一位顶尖的短视频带货文案拆解专家，擅长将口播文案拆解为结构统一、颗粒度到秒、可直接指导编导复刻的标准化报告。",',
    '        "",',
    '        "## 输入数据",',
    '        "INPUT_DATA_PLACEHOLDER",',  # 动态替换
    '        "",',
    '        "## 任务",',
    '        "严格按照以下九节结构输出，每节必须有实质内容，不允许参照原文或此处省略。",',
    '        "",',
    '        "### 一句话总结（一行）",',
    '        "格式：核心结论 · 流量打法 · 叙事主权破局点，三点用箭头连接。",',
    '        "",',
    '        "### 第一节 · 原文基础信息",',
    '        "- 逐字稿全文（保留原文，只做繁转简）",',
    '        "- 表层口播逻辑：用箭头连接，不超过6步",',
    '        "",',
    '        "### 第二节 · 深度反向拆解",',
    '        "- 风格调性（1句话）",',
    '        "- 观众心理路径（时间顺序，3到5个转折点）",',
    '        "- 3到5条可迁移底层情绪（人性驱动，不是表面技巧）",',
    '        "- 叙事主权4步拆解：",',
    '        "  1. 破霸权：具体是什么谎言或霸权",',
    '        "  2. 建标准：用什么事实或数据重建标准",',
    '        "  3. 立人设：主角的人设是什么",',
    '        "  4. 收闭环：怎么把情绪转化为信任",',
    '        "- 跑量优势（3条，简短）",',
    '        "",',
    '        "### 第三节 · 口播逐段拆解",',
    '        "用表格输出，包含：预估时长、内容模块、原文内容、核心作用、叙事主权标注、算法增益、5A标注。",',
    '        "模块分类：开场钩子、产品介绍、效果展示、信任背书、行动召唤、其他。",',
    '        "叙事主权标注：破霸权、建标准、立人设、收闭环。",',
    '        "算法增益：完播驱动、点赞驱动、评论驱动、分享驱动、关注驱动。",',
    '        "5A标注：A1（3秒）、A2（前三分位）、A3（中段）、A4（后三分位）、A5（结尾）。",',
    '        "",',
    '        "### 第四节 · 分镜头拆解",',
    '        "用表格输出，包含：镜头编号、时长、景别加运镜、画面内容、对应口播、情绪流转、视觉实锤。",',
    '        "景别：特写、近景、中景、全景、远景、文字展示。运镜：固定、推进、拉远、摇镜、跟拍、升降。",',
    '        "视觉实锤：具体画面细节，不允许省略。",',
    '        "",',
    '        "### 第五节 · 5A人群流转",',
    '        "用表格输出，包含：人群层级、作用强度（1到5星）、核心流转价值、完整流转路径。",',
    '        "",',
    '        "### 第六节 · 爆款文案库",',
    '        "用表格输出，包含：文案分类、文案内容、预估转化率、预估完播率、使用场景。",',
    '        "每模块至少3条替代文案，保持原文人设语气。",',
    '        "文案分类：开场钩子、产品卖点、效果描述、信任背书、行动召唤。",',
    '        "",',
    '        "### 第七节 · 可复刻对标行业",',
    '        "3到5个相邻品类，每条格式：推翻 X 旧叙事、然后建立 Y 新标准。",',
    '        "",',
    '        "### 第八节 · 团队落地执行要点",',
    '        "5到6条，每条一条可执行指令。",',
    '        "- 【叙事一致性】：……",',
    '        "- 【实锤优先】：……",',
    '        "- 【背书强化】：……",',
    '        "- 【反攻击预案】：……",',
    '        "- 【人群侧重】：……",',
    '        "- 【分镜实操】：……",',
    '        "",',
    '        "## 约束",',
    '        "- 基于原文事实，不编造数据；缺失信息用【推断】标注",',
    '        "- 时间轴秒级，覆盖率100%，不允许其余部分同理",',
    '        "- 替代文案语气和情绪强度与原文一致，不可降维",',
    '        "- 全部用Markdown标准表格输出",',
    '    ]',
    '    user_prompt_lines[3] = input_data_str',
    '    user_prompt = "\\n".join(user_prompt_lines)',
    '    payload = {',
    '        "model": "glm-4-flash",',
    '        "messages": [',
    '            {"role": "system", "content": system_prompt},',
    '            {"role": "user", "content": user_prompt}',
    '        ],',
    '        "temperature": 0.3,',
    '        "max_tokens": 8192',
    '    }',
    '    try:',
    '        resp = requests.post(',
    '            base_url + "/chat/completions",',
    '            headers=headers_dict, json=payload, timeout=120',
    '        )',
    '        if resp.status_code == 200:',
    '            data = resp.json()',
    '            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")',
    '            return {"report": content, "available": True, "model": "glm-4-flash"}',
    '        else:',
    '            return {',
    '                "error": "API error " + str(resp.status_code) + ": " + resp.text[:200],',
    '                "available": True',
    '            }',
    '    except Exception as e:',
    '        return {"error": str(e), "available": True}',
    '',
    '',
    '@app.route("/api/analyze-copy", methods=["POST"])',
    'def api_analyze_copy():',
    '    try:',
    '        body = request.get_json()',
    '    except Exception:',
    '        return jsonify({"error": "Invalid JSON body"}), 400',
    '    transcription = body.get("transcription", {})',
    '    analysis = body.get("analysis", {})',
    '    video_meta = body.get("video_meta", {})',
    '    full_text = transcription.get("text", "") or transcription.get("fullText", "")',
    '    if not full_text:',
    '        return jsonify({"error": "No transcription text available"}), 400',
    '',
    '    segments = transcription.get("segments", [])',
    '    seg_lines = []',
    '    for s in segments:',
    '        seg_lines.append(',
    '            "[" + str(s.get("start", 0)) + "s-" + str(s.get("end", 0)) + "s] " + s.get("text", "")',
    '        )',
    '    seg_text = "\\n".join(seg_lines)',
    '',
    '    content_type = analysis.get("contentType", {}) or {}',
    '    frames = analysis.get("frames", [])',
    '    frame_lines = []',
    '    for f in frames[:20]:',
    '        frame_lines.append(',
    '            "- " + str(round(f.get("t", 0), 1)) + "s | "',
    '            "亮度:" + str(round(f.get("brightness", 0), 3)) + " | "',
    '            "主色:" + f.get("dominantColor", "N/A") + " | "',
    '            "景别:" + f.get("shotType", "N/A") + " | "',
    '            "字幕:" + ("有" if f.get("textRatio", 0) > 5 else "无") + " | "',
    '            "人物:" + ("有" if f.get("skinRatio", 0) > 0.05 else "无")',
    '        )',
    '    phase_lines = []',
    '    for p in analysis.get("phases", []):',
    '        phase_lines.append(',
    '            "- " + p.get("label", "") + " "',
    '            "(@" + str(round(p.get("start", 0))) + "s-" + str(round(p.get("end", 0))) + "s, "',
    '            str(round(p.get("end", 0) - p.get("start", 0), 1)) + "秒)"',
    '        )',
    '',
    '    kw = transcription.get("keywords", {}) or {}',
    '    input_data_str = (',
    '        "【视频基本信息】\\n"',
    '        "- 文件名：" + analysis.get("name", "未知") + "\\n"',
    '        "- 时长：" + str(round(analysis.get("duration", 0), 1)) + "秒\\n"',
    '        "- 分辨率：" + str(video_meta.get("width", 0)) + "x" + str(video_meta.get("height", 0)) + "\\n"',
    '        "- 内容类型：" + content_type.get("label", "未知") + " - " + content_type.get("desc", "") + "\\n\\n"',
    '        "【逐字稿（按时间分段）】\\n" + seg_text + "\\n\\n"',
    '        "【帧画面摘要（前20帧）】\\n" + "\\n".join(frame_lines) + "\\n\\n"',
    '        "【场景分段】\\n" + "\\n".join(phase_lines) + "\\n\\n"',
    '        "【关键词】\\n"',
    '        "高频词：" + str(kw.get("highFreq", [])[:20]) + "\\n"',
    '        "动作词：" + str(kw.get("actions", [])[:10]) + "\\n"',
    '        "情绪词：" + str(kw.get("emotions", [])[:10]) + "\\n"',
    '    )',
    '',
    '    result = call_llm_analyze(input_data_str)',
    '    return jsonify({',
    '        "status": "ok",',
    '        "has_llm": result.get("available", False),',
    '        "report": result.get("report", None),',
    '        "error": result.get("error", None),',
    '        "segments_count": len(segments),',
    '        "frames_count": len(frames),',
    '        "full_text_length": len(full_text),',
    '        "model": result.get("model", None)',
    '    })',
]

# 写入新文件
out_lines = prefix_lines + new_lines
content = '\n'.join(out_lines)

f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'w', encoding='utf-8')
f.write(content)
f.close()

print(f'Written {len(content)} chars, {out_lines.__len__()} lines')

# 验证语法
try:
    ast.parse(content)
    print('SYNTAX OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR at line {e.lineno}: {e.msg}')
    ctx = content.split('\n')
    for di in range(-2, 4):
        li = e.lineno - 1 + di
        if 0 <= li < len(ctx):
            print(f'  [{li+1}] {repr(ctx[li][:100])}')
