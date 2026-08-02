fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# Find the speechTimeline innerHTML template
st = data.find(b"speechTimeline').innerHTML =")
bt_open = data.find(b"`", st)

# Find all ); from bt_open onwards
semi = bt_open
count = 0
while count < 10:
    semi = data.find(b');', semi+1)
    if semi < 0:
        break
    # Show context around each );
    print(f"\n); at: {semi}")
    print(f"  Context: {repr(data[semi-30:semi+10])}")
    count += 1
