fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

search = b'<br>\r\n        );\r\n    }'
pos = data.find(search)
print("Pattern found at:", pos)

if pos >= 0:
    bt_pos = pos - 1
    print("Backtick position:", bt_pos)
    print("Char at bt_pos:", repr(bytes([data[bt_pos]])))
    print("Context:", repr(data[bt_pos-20:bt_pos+30]))
    end = data.find(b'\r\n    }', pos)
    print("End section:", repr(data[pos:end+10]))
