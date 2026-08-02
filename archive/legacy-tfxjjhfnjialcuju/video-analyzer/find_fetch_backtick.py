fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# Find the fetch URL in v3
fetch_url = b'http://192.168.0.8:8766'
pos = data.find(fetch_url)
print(f"fetch URL at byte: {pos}")

if pos >= 0:
    # Find the opening backtick for this template literal
    # Search backwards from the URL for a backtick
    bt_search = data.rfind(b'`', 0, pos)
    print(f"Opening backtick at: {bt_search}")
    print(f"Context: {repr(data[bt_search-50:bt_search+50])}")
    
    # Count total backticks from bt_search to pos
    bts = [i for i in range(bt_search, pos) if data[i] == 96]
    print(f"Backticks between {bt_search} and {pos}: {len(bts)}")
    print(f"Positions: {bts}")
