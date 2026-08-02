import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Extract just the JS from <script> without the HTML
m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if m:
    js = m.group(1)
    # Check for unclosed braces/parens/brackets in the JS
    brace_count = 0
    paren_count = 0
    bracket_count = 0
    template_depth = 0
    in_single_quote = False
    in_double_quote = False
    in_template = False
    in_comment_block = False
    in_comment_line = False
    
    lines = js.split('\n')
    for i, line in enumerate(lines):
        ch_idx = 0
        while ch_idx < len(line):
            c = line[ch_idx]
            
            # Handle line comments
            if not in_comment_block and not in_double_quote and not in_single_quote and not in_template:
                if c == '/' and ch_idx + 1 < len(line) and line[ch_idx + 1] == '/':
                    break  # rest of line is comment
                if c == '/' and ch_idx + 1 < len(line) and line[ch_idx + 1] == '*':
                    in_comment_block = True
                    ch_idx += 2
                    continue
            
            if in_comment_block:
                if c == '*' and ch_idx + 1 < len(line) and line[ch_idx + 1] == '/':
                    in_comment_block = False
                    ch_idx += 2
                    continue
                ch_idx += 1
                continue
            
            if c == '\\':
                ch_idx += 2
                continue
            
            if not in_single_quote and not in_double_quote and not in_template:
                if c == "'":
                    in_single_quote = True
                elif c == '"':
                    in_double_quote = True
                elif c == '`':
                    in_template = True
                    template_depth += 1
                elif c == '{':
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                elif c == '(':
                    paren_count += 1
                elif c == ')':
                    paren_count -= 1
                elif c == '[':
                    bracket_count += 1
                elif c == ']':
                    bracket_count -= 1
            elif in_single_quote:
                if c == "'":
                    in_single_quote = False
            elif in_double_quote:
                if c == '"':
                    in_double_quote = False
            elif in_template:
                if c == '`':
                    template_depth -= 1
                    if template_depth <= 0:
                        in_template = False
                        template_depth = 0
                elif c == '$' and ch_idx + 1 < len(line) and line[ch_idx + 1] == '{':
                    template_depth += 1
                    ch_idx += 1
                elif c == '\\':
                    ch_idx += 1
            
            ch_idx += 1
    
    print(f"Braces: {brace_count} (should be 0)")
    print(f"Parens: {paren_count} (should be 0)")
    print(f"Brackets: {bracket_count} (should be 0)")
    print(f"In template: {in_template}")
    print(f"In single quote: {in_single_quote}")
    print(f"In double quote: {in_double_quote}")
    print(f"In comment block: {in_comment_block}")
    
    if brace_count != 0:
        # Find where the unbalance starts
        print("\nSearching for unclosed braces...")
        brace_count = 0
        for i, line in enumerate(lines):
            ch_idx = 0
            while ch_idx < len(line):
                c = line[ch_idx]
                if c == '{':
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                if brace_count < 0:
                    print(f"Extra closing brace at L{i+1}: {line.strip()[:60]}")
                    brace_count = 0
                ch_idx += 1
        if brace_count > 0:
            print(f"Missing {brace_count} closing brace(s)")
            # Show last 20 lines
            print("\nLast 20 lines of JS:")
            for i in range(max(0, len(lines)-20), len(lines)):
                print(f"L{i+1}: {lines[i].rstrip()}")
