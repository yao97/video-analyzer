fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# The innerHTML template literal starts at 45432
start = 45432
# Find the closing backtick - it's after <br> and before );
# Look for the pattern: <br> followed by CRLF then );
end_search_start = data.find(b'<br>', start)
print(f"<br> at: {end_search_start}")
if end_search_start > 0:
    # Show bytes from <br> to 100 bytes after
    chunk = data[end_search_start:end_search_start+100]
    print(repr(chunk))
