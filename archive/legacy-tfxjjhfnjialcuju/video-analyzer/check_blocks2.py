fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

print("L1465:", lines[1464].rstrip())
print("L1612:", lines[1611].rstrip())
print()
print("L1613:", lines[1612].rstrip())
print("L1622:", lines[1621].rstrip())
print()
print("L1623:", lines[1622].rstrip())
print("L1634:", lines[1633].rstrip())
print()
for i in range(1634, 1641):
    if i < len(lines):
        print("L" + str(i+1) + ":", lines[i].rstrip())

# Find processFile line
pf = "async function processFile"
for i, line in enumerate(lines):
    if pf in line:
        print("\nprocessFile at line:", i+1)
        break

# Find the speechTimeline innerHTML closing </div>` in source
content = "".join(lines)
bu = content.find("Backend unavailable")
div_close = content.find("</div>`", bu)
print("\nsource </div>` at char offset:", div_close)

# Find line number of </div>`
cum = 0
for i, line in enumerate(lines):
    cum += len(line)
    if cum > div_close:
        print("source </div>` on line:", i+1)
        print("Line content:", repr(line))
        break
