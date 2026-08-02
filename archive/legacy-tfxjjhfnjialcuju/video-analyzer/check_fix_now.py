fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

bu = data.find(b"Backend unavailable")
eq_bt = data.find(b"= `", bu)
print("= ` at:", eq_bt)

# Show the boundary area (around the <br> position)
br_area = eq_bt + 200 - 100  # Look around the last part
chunk = data[eq_bt:eq_bt+300]
print("\nFull chunk (decoded):")
print(chunk.decode('utf-8', errors='replace'))

# Count backticks
bt_positions = [eq_bt+i for i, b in enumerate(chunk) if b == 96]
print(f"\nBackticks in chunk at relative positions: {bt_positions}")
print(f"And absolute positions: {[eq_bt+p for p in bt_positions]}")
