fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# The broken occurrence: search for the CRLF before "const phaseLogic" 
# within the innerHTML template literal context
# Broken pattern: speechTimeline').innerHTML = `<div...><code sty...font-size:0.75rem;">\r\n\r\n    const phaseLogic
# Need to insert </code>`); before the final backtick

broken_open = b"speechTimeline').innerHTML = `<div style=\"color:var(--yellow);font-size:0.8rem;padding:1rem 0;\">\r\n        &#9888; \xe8\xbd\xac\xe5\x86\x99\xe6\x9c\x8d\xe5\x8a\xa1\xe6\x9c\xaa\xe5\x90\xaf\xe5\x8a\xa8\xe3\x80\x82\xe8\xaf\xb7\xe5\x85\x88\xe8\xbf\x90\xe8\xa1\x8c\xe4\xbb\xa5\xe4\xb8\x8b\xe5\x91\xbd\xe4\xbb\xa4\xe5\x90\xaf\xe5\x8a\xa8\xe6\x9c\x8d\xe5\x8a\xa1\xef\xbc\x9a<br>\r\n        <code style=\"background:#232636;padding:0.3rem 0.6rem;border-radius:6px;display:inline-block;margin-top:0.5rem;font-size:0.75rem;\">\r\n\r\n    const phaseLogic"
idx = data.find(broken_open)
print(f"Broken pattern at byte: {idx}")

if idx < 0:
    print("NOT FOUND - searching for partial")
    # Try shorter pattern
    short = b"speechTimeline').innerHTML = `<div style=\"color:var(--yellow)"
    idx2 = data.find(short)
    print(f"Short pattern at: {idx2}")
    # Show context
    if idx2 >= 0:
        chunk = data[idx2:idx2+400]
        print(chunk.decode('utf-8', errors='replace'))
else:
    # The fix: insert </code>`);  right before the final closing backtick of the template
    # The closing backtick is at the position where </code style=...> ends + then there's \r\n\r\n    const phaseLogic
    # We need to insert </code>`); before the \r\n\r\n    const phaseLogic
    insert_at = idx + len(broken_open) - len(b"    const phaseLogic")
    print(f"Insert fix at byte: {insert_at}")
    print(f"Content at insert point: {repr(data[insert_at-5:insert_at+30])}")
    
    fix = b"</code>`);\n    }" + b"\n\n    "
    new_data = data[:insert_at] + fix + data[insert_at + len(b"\r\n\r\n    "):]
    
    with open(fpath, "wb") as f:
        f.write(new_data)
    
    print(f"Done. Old: {len(data)} bytes, New: {len(new_data)} bytes")
