fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Check what's at lines 1465-1612 (RENDER_REPORT)
print("=== RENDER_REPORT block(1465, 1612) ===")
print(f"L1465: {lines[1464]!r}")
print(f"L1612: {lines[1611]!r}")

# Find the function that contains line 1465
for i in range(1464, 0, -1):
    if 'function' in lines[i]:
        print(f"Function at L{i+1}: {lines[i].strip()}")
        break

# Find where processFile's else block ends (</div>`) in the source
bu = "".join(lines).find("Backend unavailable")
# Find the closing </div>` of the speechTimeline innerHTML
div_close = "".join(lines).find("</div>`", bu)
print(f"\nsource </div>` at offset: {div_close}")

# In source, find which line number that is
cum = 0
for i, line in enumerate(lines):
    cum += len(line)
    if cum > div_close:
        print(f"source </div>` is on line: {i+1}")
        print(f"Content: {lines[i]!r}")
        break

# Find processFile function start and end
pf = "".join(lines).find("async function processFile")
for i, line in enumerate(lines):
    cum = sum(len(l) for l in lines[:i])
    if cum > pf:
        print(f"\nprocessFile starts at line: {i+1}")
        break

# Find where processFile ends (last `}` before `// Render Functions`)
rf_marker = "".join(lines).find("// Render Functions")
for i in range(len(lines)-1, 0, -1):
    cum = sum(len(l) for l in lines[:i])
    if cum < rf_marker:
        # Check if this is the closing } of processFile
        line = lines[i]
        if line.strip() == '}' and i > 1000:
            # Check context - should be inside processFile
            print(f"Last } before Render Functions at line {i+1}: {lines[i-1]!r} -> {line!r}")
            break

# Check DOWNLOAD_REPORT block
print(f"\n=== DOWNLOAD_REPORT block(1613, 1622) ===")
print(f"L1613: {lines[1612]!r}")
print(f"L1622: {lines[1621]!r}")
# Check DOWNLOAD_FRAMES block
print(f"\n=== DOWNLOAD_FRAMES block(1623, 1634) ===")
print(f"L1623: {lines[1622]!r}")
print(f"L1634: {lines[1633]!r}")
# Check INIT_CODE block
print(f"\n=== INIT_CODE block(1635, 1640) ===")
for i in range(1634, 1640):
    if i < len(lines):
        print(f"L{i+1}: {lines[i]!r}")
