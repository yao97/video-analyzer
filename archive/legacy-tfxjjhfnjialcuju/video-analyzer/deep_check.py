fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# Find the speechTimeline innerHTML template
st = data.find(b"speechTimeline').innerHTML =")
bu = data.find(b"Backend unavailable")
print("speechTimeline innerHTML:", st)
print("BU:", bu)

# Get the exact template boundaries
bt_open = data.find(b"`", st)
print("Template open:", bt_open)

# Find all backticks from bt_open to bt_open+300
bts = [(bt_open+i, data[bt_open+i]) for i in range(300) if data[bt_open+i] == 96]
print(f"\nBackticks from {bt_open} to {bt_open+300}:")
for pos, b in bts:
    print(f"  {pos}: backtick, next 10 chars: {repr(data[pos+1:pos+11])}")

# Find the first `); after bt_open
semi = data.find(b');', bt_open)
print(f"\nFirst ); after template open: {semi}")
print(f"Context: {repr(data[semi-20:semi+20])}")
