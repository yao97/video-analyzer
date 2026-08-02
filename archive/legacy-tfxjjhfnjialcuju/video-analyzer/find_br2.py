fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# Find the Backend unavailable section
bu = data.find(b"Backend unavailable")
print("Backend unavailable at:", bu)

# Find the first <br> after it
br1 = data.find(b'<br>', bu)
print("First <br> after BU at:", br1)
if br1 >= 0:
    print("Context:", repr(data[br1-10:br1+30]))

# Find the second <br> after it (might be in the same template or different)
# Actually the first <br> might be the one we want
# Let's also find all <br> in the area up to 5000 bytes after BU
area_end = bu + 5000
br_in_area = [i for i in range(bu, area_end) if data[i:i+4] == b'<br>']
print("All <br> in first 5000 bytes of BU section:", br_in_area)
for b in br_in_area:
    print(f"  {b}:", repr(data[b-5:b+15]))
