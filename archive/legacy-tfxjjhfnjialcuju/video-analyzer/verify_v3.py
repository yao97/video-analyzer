import re

fpath = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html"
with open(fpath, "r", encoding="utf-8") as f:
    html = f.read()

# Extract JS
m = re.search(r'<script>\s*([\s\S]*?)\s*</script>\s*</body>', html)
if m:
    js = m.group(1)
    # Find processFile
    pf = js.find("async function processFile")
    if pf >= 0:
        # Find the else block (Backend unavailable)
        bu = js.find("Backend unavailable", pf)
        # Extract ~50 lines from the else block
        chunk = js[bu-30:bu+500]
        print("processFile else block:")
        print(chunk)
        
        # Check for the closing </div>` of innerHTML
        div_close = chunk.find("</div>`")
        if div_close >= 0:
            print("\nFOUND </div>` closing template literal")
        else:
            print("\nMISSING </div>` closing template literal!")
