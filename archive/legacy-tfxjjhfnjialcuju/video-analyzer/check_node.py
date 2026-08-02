import re, subprocess

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Extract the JS from <script>
match = re.search(r'<script>\s*(.*?)\s*</script>', html, re.DOTALL)
if not match:
    print("No script found!")
else:
    js = match.group(1)
    print(f"JS length: {len(js)} chars")
    jspath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\temp_check.js"
    with open(jspath, "w", encoding="utf-8") as f:
        f.write(js)
    print("Written to temp JS file")
