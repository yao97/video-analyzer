$html = [System.IO.File]::ReadAllText("C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html")
$idx = $html.IndexOf("speechTimeline').innerHTML")
Write-Host "Found at: $idx"
$snippet = $html.Substring([Math]::Max(0, $idx - 300), 350)
Write-Host "Context:"
Write-Host $snippet
