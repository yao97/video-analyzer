fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Find the duplicate HELPER_FUNCTIONS block in the v3 HTML
# Look for the pattern: after COLOR_RGB, there's setBadge, then setStep
# The duplicate starts with: const show = id =>... (second occurrence)

first_show = html.find("const show = id =>")
print(f"First const show at: {first_show}")

# Find second occurrence
second_show = html.find("const show = id =>", first_show + 1)
print(f"Second const show at: {second_show}")

# The duplicate block goes from second_show to the end of the duplicate
# (ends right before COLOR_RGB which is the real next block)
# COLOR_RGB starts with: const COLOR_RGB = {
color_rgb_pos = html.find("const COLOR_RGB = {", second_show)
print(f"COLOR_RGB at: {color_rgb_pos}")

# The duplicate block: from second_show to just before COLOR_RGB
# It includes: \n    const show = ...\n    const hide = ...\n    const toast = ...\n    const switchTab = ...
# Let me check what's between second_show and COLOR_RGB
between = html[second_show:color_rgb_pos]
print(f"Duplicate block ({len(between)} chars):")
print(repr(between[:200]))
