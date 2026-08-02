fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "rb") as f:
    data = f.read()

# Occurrence 1 is the broken one at byte 51039
# Show more bytes after it
broken_pos = 51039
chunk = data[broken_pos:broken_pos+600]
print("Raw bytes from broken section:")
# Find where the <code> tag closes
print(chunk[200:400].decode('utf-8', errors='replace'))
print()
# Find the position of "const phaseLogic" after the broken section
const_pos = data.find(b'const phaseLogic', broken_pos)
print(f"const phaseLogic at byte: {const_pos}")
print(f"Distance from broken start: {const_pos - broken_pos}")
# Show bytes between broken start and const
between = data[broken_pos+400:const_pos]
print(f"\nBetween (400 to const): {repr(between)}")
