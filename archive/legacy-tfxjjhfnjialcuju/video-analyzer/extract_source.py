import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    content = f.read()

# Find the processFile function
pf_start = content.find("async function processFile")
print("processFile at:", pf_start)

# Find the speechTimeline innerHTML in the else branch
bu = content.find("Backend unavailable", pf_start)
print("Backend unavailable in processFile at:", bu)

# Extract the else branch
# Find the else { before BU
else_start = content.rfind("} else {", 0, bu)
print("else { at:", else_start)
print("Context:", repr(content[else_start:bu+50]))

# Find the complete else block
# Look for the closing }
# We need to find where this else block ends
# In the source, the else block should be contained within processFile
# Let's find the next } that closes the else
# by counting braces from else_start
depth = 0
in_else = False
i = else_start
while i < len(content):
    c = content[i]
    if c == '{':
        depth += 1
        in_else = True
    elif c == '}':
        depth -= 1
        if in_else and depth == 0:
            print(f"else block ends at: {i}")
            print("else block:", repr(content[else_start:i+1]))
            break
    i += 1
