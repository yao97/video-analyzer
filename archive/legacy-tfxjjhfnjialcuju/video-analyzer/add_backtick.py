fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = bytearray(f.read())

# Pattern: <br>\r\n        );
# Insert ` before <br> (at the position of <br>)
# Actually: the template literal opens with ` before <div...>, we need to close with ` after <br>>
# The <br>> ends at byte 50532, so we insert ` at 50533
search = b'<br>\r\n        );\r\n    }\r\n\r\n    const phaseLogic'
pos = data.find(search)
print("Pattern found at:", pos)

if pos >= 0:
    print("Context:", repr(bytes(data[pos-5:pos+40])))
    # Insert a backtick right before <br>
    insert_at = pos
    data.insert(insert_at, ord('`'))
    print("Inserted backtick at byte:", insert_at)
    
    with open(fpath, "wb") as f:
        f.write(data)
    print("File written")
    
    # Verify
    with open(fpath, "rb") as f:
        verify = f.read()
    new_pos = verify.find(search)
    print("New context:", repr(verify[new_pos-5:new_pos+45]))
