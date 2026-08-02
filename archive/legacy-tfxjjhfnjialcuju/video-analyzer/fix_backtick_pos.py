fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = bytearray(f.read())

# Check current state
print("Char at 50533:", chr(data[50533]), repr(bytes([data[50533]])))
print("Char at 50534:", chr(data[50534]), repr(bytes([data[50534]])))
print("Char at 50535:", chr(data[50535]), repr(bytes([data[50535]])))
print("Char at 50536:", chr(data[50536]), repr(bytes([data[50536]])))
print("Char at 50537:", chr(data[50537]), repr(bytes([data[50537]])))

# Current bytes 50533-50537: ` b r > \r
# We want: b r > ` \r

# Step 1: Delete the backtick at 50533
del data[50533]
print("Deleted backtick at 50533")

# Now what was at 50534 (b) is now at 50533
# What was at 50536 (>) is now at 50535
# What was at 50537 (\r) is now at 50536

print("After delete:")
print("Char at 50534:", chr(data[50534]))
print("Char at 50535:", chr(data[50535]))
print("Char at 50536:", chr(data[50536]))
print("Char at 50537:", chr(data[50537]))

# Step 2: Insert closing backtick at 50537 (after >)
data.insert(50537, ord('`'))
print("Inserted backtick at 50537")

print("After insert:")
print("Char at 50533:", chr(data[50533]))
print("Char at 50534:", chr(data[50534]))
print("Char at 50535:", chr(data[50535]))
print("Char at 50536:", chr(data[50536]))
print("Char at 50537:", chr(data[50537]))
print("Char at 50538:", chr(data[50538]))
print("Char at 50539:", chr(data[50539]))

with open(fpath, "wb") as f:
    f.write(data)
print("Written!")
