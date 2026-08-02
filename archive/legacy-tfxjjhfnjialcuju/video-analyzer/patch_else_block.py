import re

# Read the CORRECT source from web_player.html
src_path = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(src_path, "r", encoding="utf-8") as f:
    src = f.read()

# Extract the correct else block for processFile (Backend unavailable section)
# Find the else { that starts the Backend unavailable block in processFile
pf_start = src.find("async function processFile")
bu = src.find("Backend unavailable", pf_start)
else_start = src.rfind("} else {", 0, bu)

# Find the end of this else block by counting braces
depth = 0
in_else = False
i = else_start
while i < len(src):
    c = src[i]
    if c == '{':
        depth += 1
        in_else = True
    elif c == '}':
        depth -= 1
        if in_else and depth == 0:
            break
    i += 1

correct_else_block = src[else_start:i+1]
print(f"Correct else block length: {len(correct_else_block)}")
print("Correct else block:")
print(correct_else_block)
print()

# Now find and replace in web_player_v3.html
v3_path = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(v3_path, "r", encoding="utf-8") as f:
    v3 = f.read()

# Find the broken else block in v3
# The broken block starts at "Backend unavailable" or its preceding else {
v3_pf = v3.find("async function processFile")
v3_bu = v3.find("Backend unavailable", v3_pf)
v3_else_start = v3.rfind("} else {", 0, v3_bu)
print(f"v3 else block starts at: {v3_else_start}")

# Find the end of the else block in v3
depth = 0
in_else = False
i = v3_else_start
while i < len(v3):
    c = v3[i]
    if c == '{':
        depth += 1
        in_else = True
    elif c == '}':
        depth -= 1
        if in_else and depth == 0:
            break
    i += 1

v3_else_end = i + 1
broken_else_block = v3[v3_else_start:v3_else_end]
print(f"Broken else block length: {len(broken_else_block)}")
print("Broken else block:")
print(broken_else_block)
print()

# Replace
new_v3 = v3[:v3_else_start] + correct_else_block + v3[v3_else_end:]
print(f"Old v3 length: {len(v3)}")
print(f"New v3 length: {len(new_v3)}")
print(f"Difference: {len(new_v3) - len(v3)}")

with open(v3_path, "w", encoding="utf-8") as f:
    f.write(new_v3)
print("Written!")
