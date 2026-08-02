fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = bytearray(f.read())

# The pattern: <br>>  (50533-50535: b r >)
# Then \r (50536)
# Then two backticks (50537, 50538)
# Then \n (50539)

# Find the double backtick at 50537-50538
if data[50537] == 96 and data[50538] == 96:
    print(f"Double backtick at 50537-50538 confirmed")
    print(f"Before: {chr(data[50535])}{chr(data[50536])}{chr(data[50537])}{chr(data[50538])}{chr(data[50539])}")
    # Delete the second backtick (50538)
    del data[50538]
    print("Deleted second backtick")
    print(f"After: {chr(data[50535])}{chr(data[50536])}{chr(data[50537])}{chr(data[50539])}")
    with open(fpath, "wb") as f:
        f.write(data)
    print("Written!")
else:
    print(f"Position 50537: {data[50537]}, 50538: {data[50538]}")
