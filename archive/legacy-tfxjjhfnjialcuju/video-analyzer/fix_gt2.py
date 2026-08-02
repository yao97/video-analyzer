fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# The previous fix used &gt; which is WRONG for JS - revert it
# and use a proper approach: split the > to avoid </code> pattern
bad = 'font-size:0.75rem;"&gt;&lt;/code&gt;`'
idx = html.find(bad)
print(f"Current (wrong) fix at: {idx}")

# The correct fix: use </code` + `> instead of </code> inside the template literal
# Actually the simplest: just remove </code> since we don't need to close the code tag
# The template literal is: <code style="..."> content (which is just whitespace/newline) </code>
# The content between <code> and </code> is empty (just newline and spaces)
# So we can just use <code style="..."></code>

# Better approach: since the template literal content is just whitespace between <code> and </code>,
# we can simply close the <code> tag immediately with />
# So: <code style="..."></code> becomes <code style="..."/>
# But this changes the fix we applied. Let me check what we have now.

if idx >= 0:
    # Revert the &gt; change
    wrong_fix = 'font-size:0.75.rem;"&gt;&lt;/code&gt;`'
    # Actually find the current wrong content
    cur = html[idx:idx+60]
    print(f"Current content: {repr(cur)}")
    
    # The correct content should be: <code style="..."></code>`); 
    # But </code> inside JS template literal might confuse the HTML parser
    # Use: <code style="..."/` + `> to break the </code> pattern
    
    # Actually simplest: just close the code tag immediately
    # <code style="..."></code> inside template literal - use /> to self-close
    correct = 'font-size:0.75rem;"/>`);'
    new_html = html.replace(bad, correct)
    print(f"New content: {repr(new_html[idx:idx+60])}")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("FIXED")
else:
    print("Wrong fix already reverted or not present")
    # Check if we still have the original bad </code>`);
    bad2 = 'font-size:0.75.rem;"></code>`'
    idx2 = html.find(bad2)
    print(f"Original bad at: {idx2}")
