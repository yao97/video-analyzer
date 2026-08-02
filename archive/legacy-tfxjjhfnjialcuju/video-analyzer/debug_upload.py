path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Find the init section
idx = content.find("// ── Init ──")
print(f"Init section at: {idx}")
if idx > 0:
    print("Init code:")
    print(content[idx:idx+800])

# Check for fileInput element
print("\n\nfileInput element:")
fi_idx = content.find('id="fileInput"')
print(f"Position: {fi_idx}")
if fi_idx > 0:
    print(content[fi_idx-50:fi_idx+100])
