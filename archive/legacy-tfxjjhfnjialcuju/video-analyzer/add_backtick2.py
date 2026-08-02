fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = bytearray(f.read())

# We need: ...\xbc\x9a`<br>...
# Currently: ...\xbc\x9a<br>...  (backtick is before <br>)
# Fix: remove the backtick before <br> and add it after >
# Current pattern: \xbc\x9a`<br>
# Target: \xbc\x9a`<br>` → NO! Target: \xbc\x9a`<br>` → yes after fix
# Wait, we have: \xbc\x9a`<br> and we want: \xbc\x9a`<br>`

# The < in <br> is at 50535 (was originally 50533 before last insert)
# Find the current pattern
search_current = b'\xbc\x9a`<br>'
pos = data.find(search_current)
print("Current pattern at:", pos)

if pos >= 0:
    print("Context:", repr(bytes(data[pos:pos+30])))
    # The backtick is at pos+3 (before <)
    # We want it at pos+7 (after >)
    # Remove the misplaced backtick at pos+3
    del data[pos+3]
    print("Deleted misplaced backtick")
    # Now < is at pos+3, > at pos+6
    # Insert backtick at pos+7 (after >)
    data.insert(pos+7, ord('`'))
    print("Inserted backtick after >")
    
    with open(fpath, "wb") as f:
        f.write(data)
    print("Written")
    
    # Verify
    with open(fpath, "rb") as f:
        v = f.read()
    vp = v.find(b'\xbc\x9a`<br>`')
    print("Correct pattern at:", vp)
    if vp >= 0:
        print("SUCCESS:", repr(v[vp:vp+20]))
