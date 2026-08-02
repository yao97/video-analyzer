import re, subprocess, sys

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Extract the JS from <script>
match = re.search(r'<script>\s*(.*?)\s*</script>', html, re.DOTALL)
if not match:
    print("No script found!")
    sys.exit(1)

js = match.group(1)
print(f"JS length: {len(js)} chars")

# Write to temp file
jspath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\temp_check.js"
with open(jspath, "w", encoding="utf-8") as f:
    f.write(js)

print(f"Written to {jspath}")

# Try to check syntax with node
node_path = r"C:\Program Files\nodejs\node.exe"
try:
    result = subprocess.run([node_path, "--check", jspath], 
                          capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        print("SYNTAX OK")
    else:
        print("SYNTAX ERROR:")
        print(result.stderr[:1000])
except FileNotFoundError:
    print("Node not found, trying deno")
    try:
        result = subprocess.run(["deno", "check", jspath],
                              capture_output=True, text=True, timeout=30)
        print(result.stdout[:500])
        print(result.stderr[:500])
    except:
        print("Neither node nor deno available")
