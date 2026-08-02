fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = bytearray(f.read())

# Confirm: byte 50535 should be > and 50536 should be \r
print(f"Byte 50535: {data[50535]} ({chr(data[50535])})")
print(f"Byte 50536: {data[50536]} ({chr(data[50536])})")
print(f"Byte 50537: {data[50537]} ({chr(data[50537])})")

if data[50535] == ord('>') and data[50536] == ord('\r'):
    # Insert closing backtick at 50536 (before \r)
    data.insert(50536, ord('`'))
    print("Inserted closing backtick before \\r")
    
    with open(fpath, "wb") as f:
        f.write(data)
    print("Written!")
    
    # Verify
    with open(fpath, "rb") as f:
        v = f.read()
    print(f"Byte 50536: {v[50536]} ({chr(v[50536])})")
    print(f"Byte 50537: {v[50537]} ({chr(v[50537])})")
    print(f"Byte 50538: {v[50538]} ({chr(v[50538])})")
else:
    print("Pattern not found!")
