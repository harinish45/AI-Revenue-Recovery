$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$scriptPath = Join-Path $PSScriptRoot 'SCRIPT.md'
$outputPath = Join-Path $PSScriptRoot 'narration.txt'
$lines = Get-Content -LiteralPath $scriptPath | Where-Object { $_ -and $_ -notmatch '^#' -and $_ -notmatch '^\*\*' }
$text = ($lines -join ' ') -replace '\s+', ' '
$text | Set-Content -LiteralPath $outputPath -Encoding utf8
Write-Output "Generated $outputPath"
