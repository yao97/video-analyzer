import subprocess, sys, os

# First, re-run build_v3.py to rebuild from clean source
# This is the cleanest approach

build_script = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\build_v3.py"
v3_output = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"

# Read build_v3.py to see its current state
with open(build_script, "r", encoding="utf-8") as f:
    build_content = f.read()

# Show key blocks
import re
for block_name in ["RENDER_REPORT", "RENDER_CHARTS", "DOWNLOAD_REPORT", "DOWNLOAD_FRAMES", "INIT_CODE"]:
    m = re.search(rf"{block_name}\s*=\s*block\((\d+),\s*(\d+)\)", build_content)
    if m:
        print(f"{block_name}: lines {m.group(1)}-{m.group(2)}")
