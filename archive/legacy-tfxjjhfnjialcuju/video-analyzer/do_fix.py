fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, encoding="utf-8") as f:
    html = f.read()

# The broken pattern: innerHTML template literal that never closes
# Find it by the unique opening: innerHTML = `<div style="color:var(--yellow)
broken_open = '$(\'speechTimeline\').innerHTML = `<div style="color:var(--yellow);font-size:0.8rem;padding:1rem 0;">\n        &#9888; 转写服务未启动。请先运行以下命令启动服务：<br>\n        <code style="background:#232636;padding:0.3rem 0.6rem;border-radius:6px;display:inline-block;margin-top:0.5rem;font-size:0.75rem;">\n'
idx = html.find(broken_open)
print(f"Broken section at: {idx}")

if idx < 0:
    print("NOT FOUND - trying partial match")
    partial = 'speechTimeline').innerHTML = `<div style="color:var(--yellow)'
    idx2 = html.find(partial)
    print(f"Partial at: {idx2}")
    if idx2 >= 0:
        snippet = html[idx2:idx2+300]
        print(repr(snippet))
else:
    # Show what follows the broken section
    end = idx + len(broken_open)
    after = html[end:end+100]
    print(f"After broken section: {repr(after)}")
    
    # The fix: close the template literal and else block
    fixed_content = broken_open + '</code>`);\n    }' + '\n\n'
    print(f"\nFix: add '{fixed_content[-20:]}' after broken section")
