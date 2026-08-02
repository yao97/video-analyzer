fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, encoding="utf-8") as f:
    html = f.read()

# Find the broken section - search for the unique opening pattern
# The pattern that appears only once
import re

# Find the first occurrence of this specific broken pattern
broken = "$('speechTimeline').innerHTML = `<div style=\"color:var(--yellow);font-size:0.8rem;padding:1rem 0;\">\n        &#9888; 转写服务未启动。请先运行以下命令启动服务：<br>\n        <code style=\"background:#232636;padding:0.3rem 0.6rem;border-radius:6px;display:inline-block;margin-top:0.5rem;font-size:0.75rem;\">"

idx = html.find(broken)
print(f"Found at index: {idx}")

if idx >= 0:
    end_broken = idx + len(broken)
    # After the broken section, what follows?
    after = html[end_broken:end_broken+50]
    print(f"Chars after broken: {repr(after)}")
    
    # The FIX: insert closing backtick + semicolon + closing brace + newlines
    # before the next content (which is \n    const phaseLogic = ...)
    fix = broken + "</code>`);\n    }" + "\n\n"
    
    # Replace in html
    new_html = html[:idx] + fix + html[end_broken:]
    
    # Verify: check that buildPhases now starts properly
    bp_idx = new_html.find("function buildPhases")
    print(f"buildPhases at: {bp_idx}")
    
    # Write back
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_html)
    
    print(f"File written. Old size: {len(html)}, New size: {len(new_html)}")
    print("FIX APPLIED")
else:
    print("Broken pattern not found!")
    # Try to find by regex
    pattern = r"speechTimeline.*?innerHTML.*?转写服务未启动"
    m = re.search(pattern, html)
    if m:
        print(f"Regex found at: {m.start()}")
        print(repr(html[m.start():m.start()+300]))
