fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# Find the broken occurrence by searching for the unique pattern:
# The unclosed template literal that goes from speechTimeline').innerHTML = `... to \r\n\r\n    const phaseLogic
# We know from the hex dump that:
# Position 51039: speechTimeline').innerHTML = `<div style="color:var(--yellow);font-size:0.8rem;padding:1rem 0;">\r\n        &#9888;...
# The <code> tag closes at font-size:0.75rem;"> followed by \r\n\r\n    const phaseLogic

# Find the pattern: font-size:0.75rem;"> followed by \r\n\r\n    const phaseLogic
search1 = b'font-size:0.75rem;">\r\n\r\n    const phaseLogic'
pos = data.find(search1)
print(f"Found pattern at: {pos}")

if pos > 0:
    # Show context
    ctx = data[pos-200:pos+50]
    print("Context:")
    print(ctx.decode('utf-8', errors='replace'))
    print()
    
    # The closing backtick is at pos - 1 (right after font-size:0.75rem;">)
    # We need to insert </code>`);  before that backtick
    
    # Actually, looking at the context: the template literal closes with just `
    # and then there's \r\n\r\n    const phaseLogic
    # The backtick is right before \r\n\r\n    const phaseLogic
    
    backtick_pos = pos - 1  # The ` before \r\n\r\n
    print(f"Closing backtick at: {backtick_pos}")
    print(f"Char at backtick_pos: {chr(data[backtick_pos])!r}")
    
    # The <code> tag is incomplete - we need to close it with </code>
    # Then close the template literal with `
    # Then the rest: `);  (end innerHTML statement) 
    # Then } (close else block)
    
    # Current: ...font-size:0.75rem;">`\r\n\r\n    const phaseLogic
    # Should be: ...font-size:0.75rem;"></code>`);\r\n    }\r\n\r\n    const phaseLogic
    
    old = b'font-size:0.75rem;">\r\n\r\n    const phaseLogic'
    new = b'font-size:0.75rem;"></code>`);\r\n    }\r\n\r\n    const phaseLogic'
    
    if data.find(old, pos - 50, pos + 50) >= 0:
        print("Pattern confirmed, replacing...")
        new_data = data.replace(old, new, 1)
        with open(fpath, "wb") as f:
            f.write(new_data)
        print(f"Done. Old: {len(data)}, New: {len(new_data)}")
    else:
        print("Pattern not found at expected location")
        # Search more broadly
        for i in range(max(0, pos-100), min(len(data), pos+100)):
            chunk = data[i:i+50]
            if b'font-size:0.75rem;">' in chunk:
                print(f"font-size:0.75rem: at {i}")
                print(data[i:i+80].decode('utf-8', errors='replace'))
