$html = [System.IO.File]::ReadAllText("C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html")
$idx = $html.IndexOf("speechTimeline').innerHTML")
$remaining = $html.Substring($idx, 2000)
Write-Host "From innerHTML (2000 chars):"
Write-Host $remaining
