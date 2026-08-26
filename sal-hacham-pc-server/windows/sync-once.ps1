. (Join-Path $PSScriptRoot "common.ps1")
$config = Import-ServerConfig
Set-ServerEnvironment $config
$python = Get-ServerPython
$logs = Join-Path $script:InstallRoot "logs"
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$log = Join-Path $logs "sync.log"
$mutex = New-Object Threading.Mutex($false, "Global\SalHachamPriceSync")
if (-not $mutex.WaitOne(0)) {
    "[$(Get-Date -Format s)] Sync skipped: previous run is still active" | Out-File -FilePath $log -Append -Encoding utf8
    exit 0
}
try {
    Set-Location $script:InstallRoot
    "[$(Get-Date -Format s)] City refresh policy check started" | Out-File -FilePath $log -Append -Encoding utf8
    & $python scripts\sync_prices.py *>> $log
    $exitCode = $LASTEXITCODE
    "[$(Get-Date -Format s)] Sync finished with code $exitCode" | Out-File -FilePath $log -Append -Encoding utf8
    if ($exitCode -eq 0) {
        $rawRoot = Join-Path $script:InstallRoot "data\raw"
        $statusRoot = Join-Path $rawRoot ".status"
        if (Test-Path $rawRoot) {
            Get-ChildItem $rawRoot -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -notlike "$statusRoot*" -and $_.LastWriteTime -lt (Get-Date).AddHours(-1) } |
                Remove-Item -Force -ErrorAction SilentlyContinue
        }
    }
    exit $exitCode
}
finally {
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
}
