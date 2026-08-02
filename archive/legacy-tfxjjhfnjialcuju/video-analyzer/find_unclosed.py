import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if m:
    js = m.group(1)
    lines = js.split('\n')
    
    # Track unclosed template literals by finding ` that opens inline HTML content
    # The template in `speechTimeline`.innerHTML = `... is the prime suspect
    # Find ALL innerHTML = ` patterns
    positions = []
    for m2 in re.finditer(r'\.innerHTML\s*=\s*`', js):
        positions.append((m2.start(), lines[:js[:m2.start()].count('\n')] if m2 else []))
    
    print(f"innerHTML = ` occurs {len(positions)} times")
    
    # More importantly, track where the template depth goes up significantly
    # Count template depth line by line
    depth = 0
    in_single = False
    in_double = False
    in_template = False
    max_template_depth = 0
    max_depth_line = 0
    
    for i, line in enumerate(lines):
        j = 0
        while j < len(line):
            c = line[j]
            if c == '\\':
                j += 2
                continue
            if not in_single and not in_double:
                if c == "'":
                    in_single = True
                elif c == '"':
                    in_double = True
                elif c == '`':
                    if in_template:
                        in_template = False
                    else:
                        in_template = True
                        depth += 1
                        if depth > max_template_depth:
                            max_template_depth = depth
                            max_depth_line = i + 1
            elif in_single:
                if c == "'":
                    in_single = False
            elif in_double:
                if c == '"':
                    in_double = False
            j += 1
    
    print(f"\nTemplate literal tracking:")
    print(f"In template at end: {in_template}")
    print(f"Max template depth: {max_template_depth} at line {max_depth_line}")
    
    if in_template:
        # Find the last opening backtick that wasn't closed
        in_template = False
        last_open = None
        for i, line in enumerate(lines):
            j = 0
            while j < len(line):
                c = line[j]
                if c == '\\':
                    j += 2
                    continue
                if not in_single and not in_double:
                    if c == "'":
                        in_single = True
                    elif c == '"':
                        in_double = True
                    elif c == '`':
                        if in_template:
                            in_template = False
                        else:
                            in_template = True
                            last_open = (i+1, j, line.strip()[:80])
                elif in_single:
                    if c == "'":
                        in_single = False
                elif in_double:
                    if c == '"':
                        in_double = False
                j += 1
        
        if in_template and last_open:
            print(f"\nUnclosed template literal starts at L{last_open[0]}, col {last_open[1]}:")
            print(f"  {last_open[2]}")
            # Show 5 lines around it
            print(f"\nContext around L{last_open[0]}:")
            for i in range(max(0, last_open[0]-3), min(len(lines), last_open[0]+5)):
                print(f"  L{i+1}: {lines[i].rstrip()}")
