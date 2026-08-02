"""Fix web_player_v3.html: wrap container with #mainLayout div, fix JS reference."""
path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

orig = content

# 1. Fix CSS: add #mainLayout{display:none} before #leftPanel rule
old1 = '#leftPanel{display:none;width:340px'
new1 = '#mainLayout{display:none}\n#leftPanel{display:none;width:340px'
assert old1 in content, "CSS anchor not found"
content = content.replace(old1, new1, 1)
print("1. CSS fix: added #mainLayout{display:none}")

# 2. Wrap <div class="container"> with <div id="mainLayout">
old2 = '<div class="container">\n    <div id="leftPanel">'
new2 = '<div id="mainLayout">\n    <div class="container">\n    <div id="leftPanel">'
assert old2 in content, f"Wrapper anchor not found. Content near container: {content[content.find('container'):content.find('container')+100]!r}"
content = content.replace(old2, new2, 1)
print("2. Wrapper fix: wrapped container with #mainLayout")

# 3. Close #mainLayout before chart.js
# Current: </div>\n</div>\n<div id="tabsSection"...\n<div class="tabs">... then later </div>\n</div>\n</div>\n<script src="chart.js">
# We need to add </div> (for mainLayout) before <script src="chart.js
old3 = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js">'
new3 = '</div>\n\n<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js">'
assert old3 in content, "Chart.js anchor not found"
content = content.replace(old3, new3, 1)
print("3. mainLayout close: added </div> before chart.js")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nDone: {len(content):,} chars, {len(content.split(chr(10)))} lines")

# Final check
lines = content.split('\n')
print("\nLast 8 lines:")
for i in range(len(lines)-8, len(lines)):
    print(f"L{i+1}: {repr(lines[i])}")
print(f"\n</div> count: {content.count('</div>')}")
print(f"<div count: {content.count('<div')}")

# Check key elements
print(f"\nvideo-active CSS: {content.count('video-active')} occurrences")
print(f"mainLayout CSS: {'#mainLayout' in content}")
print(f"processFile exists: {'async function processFile' in content}")
print(f"renderCharts exists: {'function renderCharts' in content}")
