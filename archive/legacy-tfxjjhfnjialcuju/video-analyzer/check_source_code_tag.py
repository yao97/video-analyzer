fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "rb") as f:
    data = f.read()

bu = data.find(b"Backend unavailable")
eq_bt = data.find(b"= `", bu)
print("Template starts at:", eq_bt)

# Find <code> and </code> in this template
code_start = data.find(b'<code', eq_bt)
code_end = data.find(b'</code>', eq_bt)
print("<code> at:", code_start)
print("</code> at:", code_end)

if code_end >= 0:
    print("Context after </code>:", repr(data[code_end:code_end+30]))

# Find the template closing backtick
# Look for `); after the <code> area
semi_bt_area = data.find(b'`<br>', eq_bt)  # backtick, <br> pattern
print("`)<br> pattern:", semi_bt_area)

# Actually let's find the closing backtick - look for );
# after the code block
if code_end >= 0:
    semi = data.find(b');', code_end)
    print("First ); after </code> at:", semi)
    if semi >= 0:
        print("Context:", repr(data[semi-20:semi+20]))
