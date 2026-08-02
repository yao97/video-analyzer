fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Check CT_META block: 1066-1232
print("=== CT_META (1066-1232) ===")
print("Start:", lines[1065].strip())
print("End:", lines[1231].strip())
print("Has processFile?", "processFile" in "".join(lines[1065:1232]))
print()

# Check what functions are in CT_META
content = "".join(lines[1065:1232])
for kw in ["function", "async function"]:
    pos = 0
    while True:
        idx = content.find(kw, pos)
        if idx < 0:
            break
        # Find the function name
        end = content.find("(", idx)
        if end > 0:
            name = content[idx+len(kw)+1:end]
            print(f"  Found {kw}: {name}")
        pos = idx + 1

# processFile is at 1093, which is inside CT_META (1066-1232)
# Let's see what's at lines 1093-1235 (processFile through the innerHTML closing)
print("\n=== processFile function ===")
print("L1093:", lines[1092].strip())
print("L1235:", lines[1234].strip())
print()

# Now find what's between CT_META end (1232) and RENDER_REPORT start (1465)
# These lines contain processFile's function body and the closing of innerHTML
print("=== Lines 1233-1464 ===")
print("L1233:", lines[1232].strip())
print("L1234:", lines[1233].strip())
print("L1464:", lines[1463].strip())
print()
print("Has renderSpeech?", "renderSpeech" in "".join(lines[1232:1464]))
print("Has renderOverview?", "renderOverview" in "".join(lines[1232:1464]))

# Find renderSpeech line number
for i, line in enumerate(lines):
    if "function renderSpeech" in line or "function renderOverview" in line:
        print(f"\n{line.strip()} at line {i+1}")

# Check what blocks currently cover processFile
# CT_META = 1066-1232, but processFile ends at 1235
# So CT_META cuts off 3 lines into processFile!
print("\n=== PROBLEM ===")
print("processFile starts at 1093")
print("CT_META ends at 1232 (covers 1093-1232, MISSING lines 1233-1235)")
print("Missing: lines 1233, 1234, 1235")
print("Line 1235:", lines[1234].strip())

# Check: does processFile continue beyond 1235?
# processFile is a big function. Where does it end?
# Let me find where processFile ends
content2 = "".join(lines)
pf_idx = content2.find("async function processFile")
# Find the function end - look for the Render Functions marker
rf_marker = content2.find("// ════ Render Functions")
print(f"\nprocessFile ends before Render Functions at char: {rf_marker}")
# Find the line number
cum = 0
for i, line in enumerate(lines):
    cum += len(line)
    if cum > rf_marker:
        print(f"Render Functions at line: {i+1}")
        break

# Count lines in processFile
pf_end_line = None
cum2 = 0
for i, line in enumerate(lines):
    cum2 += len(line)
    if cum2 > pf_idx:
        pf_start_line = i + 1
        break
cum3 = 0
for i, line in enumerate(lines):
    cum3 += len(line)
    if cum3 > rf_marker:
        pf_end_line = i  # last line before Render Functions
        break
print(f"processFile spans lines: {pf_start_line} to {pf_end_line}")
