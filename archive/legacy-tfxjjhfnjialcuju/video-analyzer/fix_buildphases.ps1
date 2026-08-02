$html = [System.IO.File]::ReadAllText("C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html")

# Find the broken section: innerHTML = `<div...> and then const phaseLogic starts
# The template literal that opens after innerHTML = never closes
$brokenStart = $html.IndexOf('$('"'"'speechTimeline'"'"').innerHTML = `')
Write-Host "broken section starts at: $brokenStart"

# Find the innerHTML section - show 200 chars before and 400 chars after
$ctxStart = [Math]::Max(0, $brokenStart - 200)
$snippet = $html.Substring($brokenStart, 400)
Write-Host "Snippet:"
Write-Host $snippet
