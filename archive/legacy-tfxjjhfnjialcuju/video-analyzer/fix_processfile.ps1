$html = [System.IO.File]::ReadAllText("C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\web_player_v3.html")
$pos = $html.IndexOf("speechTimeline').innerHTML = `")
$fixed = $html.Substring(0, $pos) + $html.Substring($pos + 300)
# Count occurrences of speechTimeline
$cnt = ([regex]::Matches($html, "speechTimeline")).Count
Write-Host "pos=$pos total=$($html.Length) speechTimeline=$cnt"
# Find the bad section - look for the unclosed template literal
$badIdx = $html.IndexOf("'speechTimeline').innerHTML = `")
Write-Host "bad section at: $badIdx"
# Find where the template literal CLOSES - look for ` followed by semicolon+newline
$templateEnd = $html.IndexOf("`;`n", $badIdx)
Write-Host "template closes at: $templateEnd"
if ($templateEnd -gt 0) {
    $snippet = $html.Substring($templateEnd, 100)
    Write-Host "After template close: $snippet"
}
