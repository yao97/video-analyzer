fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player.html"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# CT_META = block(1066, 1246) = lines[1065:1245] = L1066-L1245
ct = "".join(lines[1065:1245])
print("CT_META length:", len(ct))
print("Has 'function buildPhases'?", "function buildPhases" in ct)
print("Has 'async function processFile'?", "async function processFile" in ct)
print("First 100 chars:", repr(ct[:100]))
print()
# Find functions in CT_META
import re
for m in re.finditer(r'function (\w+)|async function (\w+)', ct):
    fn = m.group(1) or m.group(2)
    print(f"  Function: {fn} at offset {m.start()}")
