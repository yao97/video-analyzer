fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, encoding="utf-8") as f:
    html = f.read()

# Find the broken innerHTML template literal
broken = "innerHTML = `<div style=\"color:var(--yellow);font-size:0.8rem;padding:1rem 0;\"\n        &#9888; 转写服务未启动。请先运行以下命令启动服务：<br>\n        <code style=\"background:#232636;padding:0.3rem 0.6rem;border-radius:6px;display:inline-block;margin-top:0.5rem;font-size:0.75rem;\">"
idx = html.find(broken)
print(f"Broken section at: {idx}")
print(f"File length: {len(html)}")

if idx >= 0:
    end_broken = idx + len(broken)
    # Show what follows
    after = html[end_broken:end_broken+200]
    print("After broken section:")
    print(repr(after))
