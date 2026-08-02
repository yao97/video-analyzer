fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = bytearray(f.read())

# Find the double backtick pattern
# After the <br> there are two backticks
# Pattern: \r\n`\r\n
# After delete_fix_backtick_pos.py, the pattern should be:
# ...<br>\r\n`\r\n...  (one backtick before \r\n)
# But we have: ...<br>\r\n``\r\n...  (two backticks)

# Find the area: look for <br> followed by \r\n``\r\n
search = b'<br>\r\n``\r\n'
pos = data.find(search)
print("Double-backtick pattern found at:", pos)

if pos >= 0:
    print("Context:", repr(data[pos:pos+20]))
    # Delete the first of the two backticks
    del data[pos+5]  # 5 bytes after <br> is the first backtick
    print("Deleted extra backtick")
    
    with open(fpath, "wb") as f:
        f.write(data)
    print("Written!")
    
    # Verify
    with open(fpath, "rb") as f:
        v = f.read()
    new_pos = v.find(search.replace(b'``', b'`'))
    print("Single backtick pattern at:", new_pos)
    print("Context:", repr(v[new_pos:new_pos+15]))
