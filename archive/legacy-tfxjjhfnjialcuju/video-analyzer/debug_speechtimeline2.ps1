$html = [System.IO.File]::ReadAllText("C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html")
$idx = $html.IndexOf("speechTimeline').innerHTML")
$end = $html.IndexOf("// Phase Logic per Content Type")
$remaining = $html.Substring($idx, $end - $idx)
Write-Host "From innerHTML to 'Phase Logic' ($($remaining.Length) chars):"
Write-Host "---START---"
Write-Host $remaining
Write-Host "---END---"
