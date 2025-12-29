param([string]$envFile = ".env")
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $pair = $_.Trim()
        if ($pair -and -not $pair.StartsWith('#')) {
            $parts = $pair -split '=', 2
            if ($parts.Length -eq 2) {
                [System.Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
            }
        }
    }
}
python bot.py
