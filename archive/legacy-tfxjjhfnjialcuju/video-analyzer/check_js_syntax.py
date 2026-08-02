"""Check for JS syntax errors in web_player.html by parsing it with a simple check."""
import re, sys

path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check 1: unclosed template literals (backticks)
# Find all backticks and check if they're properly paired
template_literals = re.findall(r'`(?:[^`\\]|\\.)*`', content)
print(f'Template literals found: {len(template_literals)}')

# Check 2: unclosed parentheses in JS (rough check)
# Just find function definitions and check if they have matching braces
js_start = content.find('<script>')
js_end = content.find('</script>')
if js_start > 0 and js_end > 0:
    js = content[js_start:js_end]
    # Count opening and closing braces
    open_braces = js.count('{')
    close_braces = js.count('}')
    print(f'JS open braces: {open_braces}, close braces: {close_braces}')
    if open_braces != close_braces:
        print('WARNING: Unmatched braces in JS!')
    
    # Count opening and closing parentheses
    open_paren = js.count('(')
    close_paren = js.count(')')
    print(f'JS open paren: {open_paren}, close paren: {close_paren}')
    if open_paren != close_paren:
        print('WARNING: Unmatched parentheses in JS!')

# Check 3: processFile function - does it have proper syntax?
idx = content.find('function processFile(')
if idx > 0:
    # Find the function body (rough)
    func_body = content[idx:idx+3000]
    # Check for missing semicolons after certain statements
    lines = func_body.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check if a line starts with a new statement but previous line doesn't end with ; or {
        if i > 0 and stripped and not stripped.startswith('//') and not stripped.startswith('*'):
            prev = lines[i-1].strip()
            if prev and not prev.endswith(';') and not prev.endswith('{') and not prev.endswith('}') and not prev.endswith(')'):
                # Could be a continuation line (inside parentheses)
                pass  # Skip for now
    print('processFile function found, length:', len(func_body))

# Check 4: Is video Preview code reachable?
if 'videoPreview' in content:
    print('videoPreview element referenced: YES')
    # Check if there's a $('videoPreview') call that might fail
    preview_refs = re.findall(r'\$[\'"]videoPreview[\'"]', content)
    print(f'videoPreview references: {len(preview_refs)}')

# Check 5: Is there a JS error that would prevent video preview?
# Check if $ function is defined
if 'function $' in content or 'const $ =' in content or 'let $ =' in content:
    print('$ function defined: YES')
else:
    print('WARNING: $ function NOT defined!')

print('\nDone checking.')
