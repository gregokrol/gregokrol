. (Join-Path $PSScriptRoot "common.ps1")
$config = Import-ServerConfig
Set-ServerEnvironment $config
$python = Get-ServerPython
$logs = Join-Path $script:InstallRoot "logs"
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$log = Join-Path $logs "api.log"
Set-Location $script:InstallRoot
"[$(Get-Date -Format s)] Starting API" | Out-File -FilePath $log -Append -Encoding utf8
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 *>> $log
exit $LASTEXITCODE
