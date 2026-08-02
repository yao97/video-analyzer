"""在 api_analyze_copy 之后插入 test-api-key 端点"""
f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', encoding='utf-8')
content = f.read()
f.close()

new_endpoint = '''

# ── API Key 验证端点 ──
@app.route("/api/test-api-key", methods=["POST"])
def api_test_api_key():
    import requests as _req
    try:
        body = request.get_json() or {}
    except Exception:
        return jsonify({"ok": False, "error": "Invalid JSON body"}), 400

    api_key = (body.get("api_key") or "").strip()
    model   = (body.get("model")   or "").strip()

    if not api_key:
        return jsonify({"ok": False, "error": "API Key 不能为空"})

    # SiliconFlow 检测（sk- 开头）
    is_sf = api_key.startswith("sk-")
    if is_sf:
        base_url = "https://api.siliconflow.cn/v1/chat/completions"
        models = [
            ("Qwen/Qwen2.5-72B-Instruct",       "Qwen2.5-72B（推荐·效果最好）"),
            ("deepseek-ai/DeepSeek-V2.5",       "DeepSeek V2.5（性价比）"),
            ("deepseek-ai/DeepSeek-V3",         "DeepSeek V3"),
            ("Qwen/Qwen2.5-14B-Instruct",       "Qwen2.5-14B"),
            ("Qwen/Qwen2.5-7B-Instruct",        "Qwen2.5-7B（速度快）"),
            ("THUDM/glm-4-9b-chat",             "GLM-4-9B"),
            ("iic/llama3.1-8b-instruct",        "Llama3.1-8B"),
            ("iic/qwen2-7b-instruct",           "Qwen2-7B"),
        ]
        default_model = "Qwen/Qwen2.5-72B-Instruct"
    else:
        base_url = os.environ.get(
            "LLM_BASE_URL",
            "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        )
        models = [
            ("glm-4-flash",  "GLM-4-Flash（默认·推荐）"),
            ("glm-4",        "GLM-4"),
            ("glm-4-plus",   "GLM-4-Plus"),
        ]
        default_model = "glm-4-flash"

    test_model = model if model else default_model

    payload = {
        "model": test_model,
        "messages": [{"role": "user", "content": "你好，返回 OK。"}],
        "max_tokens": 10,
        "temperature": 0,
    }

    try:
        resp = _req.post(
            base_url + "/chat/completions",
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            return jsonify({
                "ok": True,
                "model": test_model,
                "provider": "SiliconFlow" if is_sf else "Zhipu/Other",
                "available_models": models,
            })
        else:
            err = resp.text[:200]
            return jsonify({
                "ok": False,
                "error": "HTTP " + str(resp.status_code) + ": " + err,
                "available_models": models,
            })
    except _req.exceptions.Timeout:
        return jsonify({
            "ok": False,
            "error": "请求超时（30秒），请检查网络或换用更快的模型",
            "available_models": models,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "available_models": models})

'''

# 在 "# ── 启动 ──" 之前插入
marker = "# ── 启动 ──"
pos = content.find(marker)
if pos == -1:
    print("ERROR: marker not found")
    exit(1)

new_content = content[:pos] + new_endpoint + "\n\n" + content[pos:]

f = open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'w', encoding='utf-8')
f.write(new_content)
f.close()

# 语法验证
import ast
try:
    ast.parse(new_content)
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR line {e.lineno}: {e.msg}")
    lines = new_content.split('\n')
    for di in range(-3, 5):
        li = e.lineno - 1 + di
        if 0 <= li < len(lines):
            print(f"  [{li+1}] {repr(lines[li][:100])}")
