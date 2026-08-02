fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Find the exact boundaries of the duplicate block
second_show = html.find("const show = id =>", html.find("const show = id =>") + 1)
color_rgb = html.find("const COLOR_RGB = {")

# The duplicate block ends just before COLOR_RGB
# Show the last 100 chars of the duplicate
dup_end = color_rgb
dup_start = second_show
dup_content = html[dup_start:dup_end]
print(f"Duplicate block ({len(dup_content)} chars):")
print(repr(dup_content[-150:]))
print()
print(f"dup_start={dup_start}, dup_end={dup_end}")

# Remove the duplicate
new_html = html[:dup_start] + html[dup_end:]
print(f"\nOld size: {len(html)}, New size: {len(new_html)}")

# Write back
with open(fpath, "w", encoding="utf-8") as f:
    f.write(new_html)

print("DONE - duplicate removed")
